"""FastAPI server for Voice AI Orchestration.

Provides endpoints for:
- LiveKit token generation
- Document upload and KB management
- System prompt management
- Agent control (start/stop)
- Transcript viewing
"""

import asyncio
import logging
import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Voice AI Orchestration API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)
PROMPT_FILE = Path("Prompt/prompt.md")
PROMPT_FILE.parent.mkdir(exist_ok=True)

# Global state
agent_process: Optional[subprocess.Popen] = None
rag_engine = None


def get_rag_engine():
    """Lazy-load RAG engine."""
    global rag_engine
    if rag_engine is None:
        from rag import RAGEngine
        rag_engine = RAGEngine(
            data_dir="Data",
            prompt_file="Prompt/prompt.md",
            index_name="knowledge-base",
            embedding_model="gemini-embedding-001",
            llm_model="llama-3.3-70b",
        )
        logger.info("RAG engine initialized")
    return rag_engine


# ─── Models ───────────────────────────────────────────────────────

class AgentStatus(BaseModel):
    running: bool
    pid: Optional[int] = None
    mode: Optional[str] = None


class StartAgentRequest(BaseModel):
    mode: str = "dev"


class PromptUpdate(BaseModel):
    prompt: str


class TokenRequest(BaseModel):
    room_name: str = "voice-agent-room"
    participant_name: str = "user"


# ─── Health ───────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    """Clear old index and uploads when a new session starts."""
    logger.info("New session starting — clearing previous index and uploads...")

    # Clear Pinecone index
    try:
        engine = get_rag_engine()
        engine.clear_index()
    except Exception as e:
        logger.warning(f"Failed to clear index on startup: {e}")

    # Clear uploads directory
    import shutil
    if UPLOADS_DIR.exists():
        for f in UPLOADS_DIR.iterdir():
            try:
                if f.is_file():
                    f.unlink()
            except Exception:
                pass
    logger.info("Startup cleanup complete")


@app.get("/")
async def root():
    return {"status": "ok", "service": "Voice AI Orchestration API"}


# ─── LiveKit Token ────────────────────────────────────────────────

@app.post("/api/token")
async def generate_token(request: TokenRequest):
    """Generate a LiveKit access token for the frontend."""
    from livekit.api import AccessToken, VideoGrants

    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL")

    if not api_key or not api_secret:
        raise HTTPException(
            status_code=500,
            detail="LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set in .env",
        )

    token = (
        AccessToken(api_key, api_secret)
        .with_identity(request.participant_name)
        .with_name(request.participant_name)
        .with_grants(VideoGrants(
            room_join=True,
            room=request.room_name,
        ))
    )

    jwt = token.to_jwt()
    return {
        "token": jwt,
        "url": livekit_url,
        "room_name": request.room_name,
    }


# ─── Document Upload & KB Management ─────────────────────────────

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document and add it to the knowledge base."""
    allowed_extensions = {".pdf", ".txt", ".md", ".docx"}
    ext = Path(file.filename).suffix.lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_extensions)}",
        )

    # Save uploaded file
    file_id = str(uuid.uuid4())[:8]
    safe_filename = f"{file_id}_{file.filename}"
    file_path = UPLOADS_DIR / safe_filename

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"File saved: {file_path}")

        # Add to RAG
        engine = get_rag_engine()
        doc_id = engine.add_document(str(file_path), file.filename)

        return {
            "id": doc_id,
            "filename": file.filename,
            "size": len(content),
            "status": "indexed",
        }

    except Exception as e:
        # Clean up on failure
        if file_path.exists():
            file_path.unlink()
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/documents")
async def list_documents():
    """List all uploaded documents in the knowledge base."""
    engine = get_rag_engine()
    docs = engine.list_documents()
    return {"documents": docs}


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from the knowledge base."""
    engine = get_rag_engine()
    deleted = engine.delete_document(doc_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"status": "deleted", "id": doc_id}


# ─── System Prompt ────────────────────────────────────────────────

@app.get("/api/prompt")
async def get_prompt():
    """Get current system prompt."""
    if PROMPT_FILE.exists():
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            prompt = f.read()
    else:
        prompt = "You are a helpful voice assistant."
    return {"prompt": prompt}


@app.put("/api/prompt")
async def update_prompt(request: PromptUpdate):
    """Update the system prompt."""
    PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        f.write(request.prompt)

    logger.info(f"System prompt updated ({len(request.prompt)} chars)")
    return {"status": "updated", "length": len(request.prompt)}


# ─── Agent Control ────────────────────────────────────────────────

@app.get("/api/agent/status", response_model=AgentStatus)
async def get_status():
    """Get current agent status."""
    global agent_process
    if agent_process and agent_process.poll() is None:
        return AgentStatus(
            running=True, pid=agent_process.pid, mode=getattr(agent_process, "mode", "dev")
        )
    return AgentStatus(running=False)


@app.post("/api/agent/start", response_model=AgentStatus)
async def start_agent(request: StartAgentRequest):
    """Start the voice agent."""
    global agent_process

    if agent_process and agent_process.poll() is None:
        raise HTTPException(status_code=400, detail="Agent is already running")

    if request.mode not in ["console", "dev"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'console' or 'dev'")

    try:
        logger.info(f"Starting agent in {request.mode} mode...")

        agent_process = subprocess.Popen(
            ["uv", "run", "python", "agent.py", request.mode],
            cwd=Path(__file__).parent,
            stdout=None,
            stderr=None,
        )
        agent_process.mode = request.mode

        await asyncio.sleep(1)

        if agent_process.poll() is not None:
            raise HTTPException(status_code=500, detail="Agent failed to start")

        logger.info(f"Agent started with PID {agent_process.pid}")
        return AgentStatus(running=True, pid=agent_process.pid, mode=request.mode)

    except Exception as e:
        logger.error(f"Failed to start agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start agent: {str(e)}")


@app.post("/api/agent/stop")
async def stop_agent():
    """Stop the voice agent."""
    global agent_process

    if not agent_process or agent_process.poll() is not None:
        raise HTTPException(status_code=400, detail="Agent is not running")

    try:
        logger.info(f"Stopping agent (PID {agent_process.pid})...")
        agent_process.terminate()
        try:
            agent_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            agent_process.kill()

        agent_process = None
        return {"status": "stopped"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop agent: {str(e)}")


# ─── Transcripts ──────────────────────────────────────────────────

@app.get("/api/transcripts")
async def get_transcripts():
    """Get list of available transcripts."""
    log_dir = Path("logs")
    if not log_dir.exists():
        return {"transcripts": []}

    transcripts = sorted(log_dir.glob("conversation_*.txt"), reverse=True)
    return {
        "transcripts": [
            {
                "filename": t.name,
                "created": t.stat().st_mtime,
                "size": t.stat().st_size,
            }
            for t in transcripts[:10]
        ]
    }


@app.get("/api/transcripts/{filename}")
async def get_transcript(filename: str):
    """Get content of a specific transcript."""
    log_dir = Path("logs")
    transcript_path = log_dir / filename

    if not transcript_path.resolve().is_relative_to(log_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript not found")

    with open(transcript_path, "r") as f:
        content = f.read()
    return {"filename": filename, "content": content}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
