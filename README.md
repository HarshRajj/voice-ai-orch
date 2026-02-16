# Voice AI Orchestration

A real-time voice agent powered by **LiveKit** with **RAG** (Retrieval-Augmented Generation) over uploaded documents. Talk to the agent via WebRTC, upload documents to build a knowledge base, and tweak the system prompt — all through a modern React UI with live streaming transcripts.

## Features

- 🎤 **Real-time voice conversations** — WebRTC via LiveKit with low-latency audio
- 📄 **Document upload** — upload PDFs, TXT, MD, DOCX to create a knowledge base
- 🧠 **RAG-powered answers** — agent retrieves context from uploaded docs and speaks the answer
- ✏️ **Editable system prompt** — customize the agent's personality and instructions live
- 📜 **Streaming transcript** — agent responses appear word-by-word in real time
- 🔍 **RAG sources panel** — see which document chunks were used to answer
- 🔇 **Smart query filtering** — agent only queries KB for real questions, skips casual chatter
- 🔄 **Session cleanup** — Pinecone index and uploads are cleared on each server restart

## Architecture

```
User Voice → Deepgram STT → Smart KB Filter → RAG Lookup (Pinecone) → OpenAI GPT-4o → Cartesia TTS → Audio Output
                                                                            ↕
                                                              Streaming Transcript → Frontend
```

| Component | Technology |
|---|---|
| Voice / WebRTC | LiveKit |
| STT | Deepgram Nova-2 |
| LLM (Voice) | OpenAI GPT-4o (via LiveKit Agents) |
| LLM (RAG Synthesis) | Cerebras Llama-3.3-70b |
| TTS | Cartesia |
| Embeddings | Google Gemini (`gemini-embedding-001`, 3072-dim) |
| Vector Store | Pinecone (serverless) |
| Backend | FastAPI + Python |
| Frontend | React + Vite + TypeScript |

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://astral.sh/uv) package manager
- Node.js 18+ and npm
- API keys (see below)

### 1. Clone and Setup

```bash
git clone <repo-url>
cd voice-ai-orch
```

### 2. Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Required API keys:

| Key | Service | Get it from |
|---|---|---|
| `LIVEKIT_URL` | LiveKit (WebRTC) | https://cloud.livekit.io |
| `LIVEKIT_API_KEY` | LiveKit | Project settings |
| `LIVEKIT_API_SECRET` | LiveKit | Project settings |
| `OPENAI_API_KEY` | Voice LLM (GPT-4o) | https://platform.openai.com/api-keys |
| `DEEPGRAM_API_KEY` | STT | https://console.deepgram.com |
| `CARTESIA_API_KEY` | TTS | https://play.cartesia.ai |
| `GOOGLE_API_KEY` | Embeddings | https://aistudio.google.com/apikey |
| `CEREBRAS_API_KEY` | RAG LLM | https://cloud.cerebras.ai |
| `PINECONE_API_KEY` | Vector Store | https://app.pinecone.io |

### 3. Install Backend Dependencies

```bash
uv sync
```

### 4. Start All Services (3 terminals)

**Terminal 1 — API Server** (http://localhost:8000):
```bash
uv run api_server.py
```

**Terminal 2 — LiveKit Voice Agent:**
```bash
uv run agent.py dev
```

**Terminal 3 — Frontend** (http://localhost:5173):
```bash
cd frontend
npm install   # first time only
npm run dev
```

### 5. Use It

1. Open **http://localhost:5173**
2. **Upload** a PDF or text document (top-left panel)
3. **Edit the prompt** if desired (top-right panel)
4. Click **Start Call** and speak
5. Ask a question about the uploaded document
6. Watch the streaming transcript + RAG sources appear in real time

## Project Structure

```
voice-ai-orch/
├── agent.py                    # Entry point for LiveKit CLI
├── api_server.py               # FastAPI backend (upload, prompt, token, agent control)
├── initialize_rag.py           # One-time RAG initialization script
├── conversation_logger.py      # Conversation transcript logger
├── voice_agent/                # Voice agent package
│   ├── __init__.py             # Exports entrypoint()
│   ├── pipeline.py             # Component factories + pipeline assembly
│   ├── voice_assistant.py      # VoiceAssistant agent (RAG + prompt orchestration)
│   └── prompt_manager.py       # 3-layer prompt system (core + persona + RAG context)
├── rag/
│   ├── __init__.py
│   └── rag_engine.py           # LlamaIndex + Pinecone RAG engine
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Main app with streaming transcript state
│   │   ├── components/
│   │   │   ├── VoiceRoom.tsx   # LiveKit room + useVoiceAssistant streaming
│   │   │   ├── PromptEditor.tsx
│   │   │   ├── DocUpload.tsx
│   │   │   ├── Transcript.tsx
│   │   │   └── RagSources.tsx
│   │   └── api/
│   │       └── client.ts       # Backend API client
│   └── package.json
├── Prompt/
│   └── prompt.md               # System prompt file
├── pyproject.toml              # Python dependencies (managed by uv)
└── .env.example                # Environment variable template
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/token` | Generate LiveKit access token |
| `POST` | `/api/upload` | Upload document to KB |
| `GET` | `/api/documents` | List uploaded documents |
| `DELETE` | `/api/documents/{id}` | Remove document from KB |
| `GET` | `/api/prompt` | Get system prompt |
| `PUT` | `/api/prompt` | Update system prompt |
| `GET` | `/api/agent/status` | Agent running status |
| `POST` | `/api/agent/start` | Start voice agent |
| `POST` | `/api/agent/stop` | Stop voice agent |
| `GET` | `/api/transcripts` | List conversation transcripts |
| `GET` | `/api/transcripts/{filename}` | Get transcript content |

## Key Design Decisions

- **Session isolation** — Pinecone index clears on server restart so each session starts fresh
- **Smart KB filtering** — casual messages ("thanks", "okay") skip the RAG pipeline to avoid irrelevant lookups
- **Streaming transcripts** — uses LiveKit's `useVoiceAssistant` hook for word-by-word agent text display
- **3-layer prompt system** — core directives (brevity, voice format) + user persona + dynamic RAG context
- **Compact RAG mode** — single LLM call for synthesis to keep latency under real-time constraints

## Known Limitations

- Single-room design — one voice call at a time
- Pinecone free tier has index limits
- Index is cleared on every server restart (by design for session isolation)

## License

MIT
