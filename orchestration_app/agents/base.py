"""
Base utilities and helper functions for agent creation and LLM initialization.
Configured for Llama (via local Ollama) as the primary provider with no Gemini dependencies.
"""
import os
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from django.conf import settings


def is_mock_mode() -> bool:
    """
    Determines whether agents should operate in mock execution mode.
    Returns True only if explicitly set via MOCK_AGENT_MODE=true.
    """
    return getattr(settings, "MOCK_AGENT_MODE", False) or (
        os.getenv("MOCK_AGENT_MODE", "").lower() in ("true", "1", "yes")
    )


def get_chat_model(
    model_name: Optional[str] = None,
    temperature: float = 0.0,
) -> BaseChatModel:
    """
    Factory creating a configured chat model instance.
    
    Defaults to Llama (via local Ollama) - no cloud API keys required.
    """
    provider = getattr(settings, "LLM_PROVIDER", None) or os.getenv("LLM_PROVIDER", "ollama")
    provider = provider.lower()

    if provider in ("ollama", "llama"):
        selected_model = (
            model_name
            or getattr(settings, "OLLAMA_MODEL", None)
            or os.getenv("OLLAMA_MODEL", "llama3.2")
        )
        base_url = (
            getattr(settings, "OLLAMA_BASE_URL", None)
            or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=selected_model,
                temperature=temperature,
                base_url=base_url,
            )
        except ImportError:
            from langchain_openai import ChatOpenAI
            v1_url = base_url.rstrip("/")
            if not v1_url.endswith("/v1"):
                v1_url += "/v1"
            return ChatOpenAI(
                model=selected_model,
                temperature=temperature,
                base_url=v1_url,
                api_key="ollama",
            )

    # Fallback to OpenAI if explicitly requested
    from langchain_openai import ChatOpenAI
    selected_model = (
        model_name
        or getattr(settings, "OPENAI_MODEL_NAME", None)
        or os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    )
    openai_key = getattr(settings, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    return ChatOpenAI(
        model=selected_model,
        temperature=temperature,
        openai_api_key=openai_key or "mock-key",
    )
