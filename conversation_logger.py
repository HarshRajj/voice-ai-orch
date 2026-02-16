"""Conversation transcript logger for Aidy agent."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ConversationLogger:
    """Logs conversation transcripts between user and agent."""

    def __init__(self, log_dir: str = "logs"):
        """Initialize conversation logger.

        Args:
            log_dir: Directory to save conversation logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create a new log file for this session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"conversation_{timestamp}.txt"
        self.json_file = self.log_dir / f"conversation_{timestamp}.json"

        self.messages = []
        self._initialize_log()

    def _initialize_log(self):
        """Initialize the log file with header."""
        with open(self.log_file, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("           AIDY CONVERSATION TRANSCRIPT\n")
            f.write(f"           Session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

        logger.info(f"Conversation log initialized: {self.log_file}")

    def log_user_message(self, message: str, timestamp: Optional[datetime] = None):
        """Log a message from the user.

        Args:
            message: User's message text
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        entry = {
            "role": "user",
            "message": message,
            "timestamp": timestamp.isoformat(),
        }
        self.messages.append(entry)

        # Append to text log (simple format)
        with open(self.log_file, "a") as f:
            f.write(f"USER: {message}\n\n")

        logger.info(f"Logged user message: {message[:50]}...")

    def log_agent_message(self, message: str, timestamp: Optional[datetime] = None):
        """Log a message from the agent.

        Args:
            message: Agent's response text
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        entry = {
            "role": "agent",
            "message": message,
            "timestamp": timestamp.isoformat(),
        }
        self.messages.append(entry)

        # Append to text log (simple format)
        with open(self.log_file, "a") as f:
            f.write(f"AIDY: {message}\n\n")

        logger.info(f"Logged agent message: {message[:50]}...")

    def log_system_event(self, event: str, timestamp: Optional[datetime] = None):
        """Log a system event (e.g., RAG lookup, error).

        Args:
            event: System event description
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        entry = {
            "role": "system",
            "message": event,
            "timestamp": timestamp.isoformat(),
        }
        self.messages.append(entry)

        # Append to text log
        with open(self.log_file, "a") as f:
            f.write(f"[{timestamp.strftime('%H:%M:%S')}] SYSTEM: {event}\n")

    def save_json(self):
        """Save conversation to JSON format for structured access."""
        with open(self.json_file, "w") as f:
            json.dump(
                {
                    "session_start": datetime.now().isoformat(),
                    "messages": self.messages,
                },
                f,
                indent=2,
            )

        logger.info(f"Conversation saved to JSON: {self.json_file}")

    def finalize(self):
        """Finalize the log with footer and save JSON."""
        with open(self.log_file, "a") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"Session ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total messages: {len(self.messages)}\n")
            f.write("=" * 80 + "\n")

        self.save_json()
        logger.info(f"Conversation log finalized: {len(self.messages)} messages")

    def get_transcript(self) -> str:
        """Get the full conversation transcript as a string.

        Returns:
            Full conversation transcript
        """
        with open(self.log_file, "r") as f:
            return f.read()
