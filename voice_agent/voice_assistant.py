"""
VoiceAssistant — LiveKit Agent with RAG-augmented responses.

Handles:
  - Receiving transcribed user speech (from STT)
  - Querying the Knowledge Base (Layer 3: RAG context)
  - Sending transcripts and RAG sources to the frontend
  - Logging conversations
"""

import json
import logging

from livekit import rtc
from livekit.agents import Agent, ChatContext, ChatMessage
from rag import RAGEngine
from conversation_logger import ConversationLogger
from voice_agent.prompt_manager import build_system_prompt

logger = logging.getLogger(__name__)




class VoiceAssistant(Agent):
    """Voice assistant that orchestrates STT → LLM → TTS with KB retrieval."""

    def __init__(
        self,
        kb_engine: RAGEngine,
        conv_logger: ConversationLogger,
        room: rtc.Room,
    ) -> None:
        self.kb_engine = kb_engine
        self.conv_logger = conv_logger
        self.room = room
        super().__init__(
            instructions=build_system_prompt(),
        )

    def _should_query_kb(self, text: str) -> bool:
        """Skip KB for very short casual messages like 'thanks' or 'bye'."""
        return len(text.split()) > 3 or "?" in text

    async def _send_data_message(self, msg_type: str, data: dict):
        """Send a data message to the room for frontend consumption."""
        try:
            payload = json.dumps({"type": msg_type, **data}).encode("utf-8")
            await self.room.local_participant.publish_data(payload, reliable=True)
        except Exception as e:
            logger.warning(f"Failed to send data message: {e}")

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage
    ):
        """
        Called after STT transcribes user speech.
        Queries the KB (Layer 3) before the LLM generates a response.
        """
        try:
            user_query = (
                new_message.text_content()
                if callable(new_message.text_content)
                else new_message.text_content
            )
        except AttributeError:
            user_query = str(new_message)

        logger.info(f"User query: {user_query}")

        # Log user message
        self.conv_logger.log_user_message(user_query)

        # Send transcript to frontend
        await self._send_data_message("transcript", {
            "role": "user",
            "text": user_query,
        })

        # Skip KB for casual conversation
        if not self._should_query_kb(user_query):
            logger.info("Skipping KB query (casual message)")
            return

        # Layer 3: KB retrieval (dynamic RAG context)
        try:
            result = await self.kb_engine.aquery_with_sources(user_query)
            rag_context = result["answer"]
            sources = result["sources"]

            logger.info(f"KB context retrieved: {rag_context[:200]}...")

            # Inject KB context into conversation for the LLM
            turn_ctx.add_message(
                role="assistant",
                content=f"[Knowledge Base Information]: {rag_context}",
            )

            # Send RAG sources to frontend
            if sources:
                await self._send_data_message("rag_sources", {
                    "query": user_query,
                    "sources": sources,
                })

        except Exception as e:
            logger.error(f"KB retrieval failed: {e}")
            # Continue without KB context — LLM responds from training data
