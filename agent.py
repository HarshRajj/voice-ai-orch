"""
Voice AI Agent — Entry point for LiveKit CLI.

All logic lives in the voice_agent/ package:
  voice_agent/pipeline.py       — Component factories + entrypoint
  voice_agent/voice_assistant.py — VoiceAssistant Agent class
  voice_agent/prompt_manager.py  — 3-layer prompt system
"""

from dotenv import load_dotenv
from livekit import agents
from voice_agent import entrypoint

load_dotenv(".env")

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
