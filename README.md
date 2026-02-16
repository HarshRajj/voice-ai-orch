# Voice AI Orchestration

A real-time voice agent powered by LiveKit with RAG (Retrieval-Augmented Generation) over uploaded documents. Users can talk to the agent via WebRTC, upload documents to build a knowledge base, and tweak the agent's system prompt — all through a modern React UI.

## Features

- 🎤 **Real-time voice conversations** over WebRTC via LiveKit
- 📄 **Document upload** — upload PDFs, TXT, MD, DOCX to create a knowledge base
- 🧠 **RAG-powered answers** — agent retrieves relevant context from uploaded documents
- ✏️ **Editable system prompt** — customize the agent's personality and instructions
- 📜 **Live transcript** — see the conversation in real-time
- 🔍 **RAG sources panel** — see which documents were used to answer
- 🔇 **Noise cancellation + VAD** — robust voice activity detection

## Architecture

```
User Voice → Deepgram STT → RAG Lookup (Pinecone) → GPT-4o → Cartesia TTS → Audio Output
```

| Component | Technology |
|---|---|
| Voice / WebRTC | LiveKit |
| STT | Deepgram Nova-2 |
| LLM (Voice) | OpenAI GPT-4o |
| LLM (RAG) | Cerebras Llama-3.3-70b |
| TTS | Cartesia |
| Embeddings | Google Gemini (`gemini-embedding-001`) |
| Vector Store | Pinecone |
| Backend | FastAPI |
| Frontend | React + Vite + TypeScript + Tailwind CSS |

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

| Key | Get it from |
|---|---|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `DEEPGRAM_API_KEY` | https://console.deepgram.com |
| `CARTESIA_API_KEY` | https://play.cartesia.ai |
| `LIVEKIT_URL` | https://cloud.livekit.io (create a project) |
| `LIVEKIT_API_KEY` | LiveKit project settings |
| `LIVEKIT_API_SECRET` | LiveKit project settings |
| `GOOGLE_API_KEY` | https://aistudio.google.com/apikey |
| `CEREBRAS_API_KEY` | https://cloud.cerebras.ai |
| `PINECONE_API_KEY` | https://app.pinecone.io |

### 3. Install Backend Dependencies

```bash
uv sync
```

### 4. Initialize RAG (Optional — for pre-loaded documents)

If you have documents in the `Data/` folder:

```bash
uv run python initialize_rag.py
```

### 5. Start Backend API Server

Terminal 1:
```bash
uv run python api_server.py
```

Runs on http://localhost:8000

### 6. Start the LiveKit Agent

Terminal 2:
```bash
uv run python agent.py dev
```

### 7. Start Frontend

Terminal 3:
```bash
cd frontend
npm install   # first time only
npm run dev
```

Runs on http://localhost:5173

### 8. Use It

1. Open http://localhost:5173
2. Go to **Documents** tab → upload a PDF or text file
3. Go to **Prompt** tab → customize the system prompt (optional)
4. Go to **Voice Call** tab → click **Start Call**
5. Speak a question about the uploaded document
6. See the transcript + RAG sources in the right panel

## Project Structure

```
voice-ai-orch/
├── agent.py                    # Entry point for LiveKit CLI
├── api_server.py               # FastAPI backend (upload, prompt, token, agent control)
├── initialize_rag.py           # One-time RAG initialization script
├── conversation_logger.py      # Conversation transcript logger
├── voice_agent/                # Voice agent package (modular)
│   ├── __init__.py             # Exports entrypoint()
│   ├── pipeline.py             # Component factories + pipeline assembly
│   ├── voice_assistant.py      # VoiceAssistant agent class
│   └── prompt_manager.py       # 3-layer prompt system
├── rag/
│   ├── __init__.py
│   └── rag_engine.py           # LlamaIndex + Pinecone RAG engine
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Main app layout
│   │   ├── components/
│   │   │   ├── VoiceRoom.tsx   # LiveKit WebRTC room
│   │   │   ├── PromptEditor.tsx
│   │   │   ├── DocUpload.tsx
│   │   │   ├── Transcript.tsx
│   │   │   └── RagSources.tsx
│   │   └── api/
│   │       └── client.ts       # Backend API client
│   └── package.json
├── Data/                       # Pre-loaded documents
├── Prompt/
│   └── prompt.md               # System prompt file
├── uploads/                    # User-uploaded documents
├── logs/                       # Conversation transcripts
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

## Known Limitations

- Single-room design — one voice call at a time
- Pinecone free tier has index/namespace limits
- Cartesia TTS requires a separate API key (could switch to OpenAI TTS)

## License

MIT
