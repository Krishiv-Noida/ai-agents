"""
Prompts package for supervisor and worker agents.
"""
from orchestration_app.prompts.supervisor_prompts import SUPERVISOR_SYSTEM_PROMPT
from orchestration_app.prompts.coder_prompts import CODER_SYSTEM_PROMPT

__all__ = ["SUPERVISOR_SYSTEM_PROMPT", "CODER_SYSTEM_PROMPT"]
