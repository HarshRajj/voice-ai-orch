"""
Pipeline — Component factories and LiveKit session composition.

Components:
  1. STT  (Deepgram Nova-2)   — speech to text
  2. LLM  (Cerebras)          — language model
  3. TTS  (Cartesia)          — text to speech
  4. KB   (Pinecone + Google) — knowledge base retrieval
"""

import logging
from livekit import agents
from livekit.agents import (
    AgentSession,
    RoomInputOptions,
    BackgroundAudioPlayer,
    AudioConfig,
    BuiltinAudioClip,
)
from livekit.plugins import deepgram, openai, cartesia, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from rag import RAGEngine
from conversation_logger import ConversationLogger
from voice_agent.voice_assistant import VoiceAssistant

logger = logging.getLogger(__name__)

# Singleton KB instance (shared across sessions)
_kb_engine = None


# ── Component Factories ──────────────────────────────────────────

def create_stt():
    """Component 1: Speech-to-Text (Deepgram Nova-2)."""
    logger.info("STT  → Deepgram Nova-2")
    return deepgram.STT(model="nova-2-general")


def create_llm():
    """Component 2: Language Model (Cerebras llama3.1-8b)."""
    logger.info("LLM  → Cerebras llama3.1-8b")
    return openai.LLM.with_cerebras(model="llama3.1-8b")


def create_tts():
    """Component 3: Text-to-Speech (Cartesia)."""
    logger.info("TTS  → Cartesia")
    return cartesia.TTS(voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc")


def create_kb():
    """Component 4: Knowledge Base (Pinecone + Google Embeddings + Cerebras)."""
    global _kb_engine
    if _kb_engine is None:
        logger.info("KB   → Pinecone + gemini-embedding-001 + Cerebras")
        _kb_engine = RAGEngine(
            data_dir="Data",
            prompt_file="Prompt/prompt.md",
            index_name="knowledge-base",
            embedding_model="gemini-embedding-001",
            llm_model="llama-3.3-70b",
        )
    return _kb_engine


# ── Entrypoint ───────────────────────────────────────────────────

async def entrypoint(ctx: agents.JobContext):
    """Compose all 4 components into the LiveKit voice pipeline."""

    conv_logger = ConversationLogger(log_dir="logs")
    logger.info(f"Session log: {conv_logger.log_file}")

    # Initialize components
    stt = create_stt()
    llm = create_llm()
    tts = create_tts()
    kb  = create_kb()

    # Build pipeline
    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=silero.VAD.load(
            activation_threshold=0.8,
            min_speech_duration=0.5,
            min_silence_duration=1.2,
        ),
        turn_detection=MultilingualModel(),
    )

    # Log agent responses (frontend gets streaming text via useVoiceAssistant hook)
    @session.on("conversation_item_added")
    def on_conversation_item(event):
        try:
            item = event.item
            if hasattr(item, "role") and item.role == "assistant":
                if hasattr(item, "content"):
                    content = item.content
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        text = " ".join(
                            block.get("text", "") if isinstance(block, dict) else str(block)
                            for block in content
                        )
                    else:
                        text = str(content)
                    if text and not text.startswith("[Knowledge Base Information]"):
                        conv_logger.log_agent_message(text)
                        # Send to frontend via data message
                        import asyncio
                        asyncio.ensure_future(
                            ctx.room.local_participant.publish_data(
                                json.dumps({
                                    "type": "transcript",
                                    "role": "agent",
                                    "text": text,
                                }).encode("utf-8"),
                                reliable=True,
                            )
                        )
        except Exception as e:
            logger.warning(f"Failed to log conversation item: {e}")

    # Start
    await session.start(
        room=ctx.room,
        agent=VoiceAssistant(kb, conv_logger, ctx.room),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Background thinking sounds
    try:
        background_audio = BackgroundAudioPlayer(
            thinking_sound=[
                AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.6),
                AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.5),
            ],
        )
        await background_audio.start(room=ctx.room, agent_session=session)
    except Exception as e:
        logger.warning(f"Background audio not available: {e}")

    # Greet
    await session.generate_reply(
        instructions="Greet the user warmly, introduce yourself as a voice assistant, "
        "and let them know they can ask questions about any documents they've uploaded."
    )
