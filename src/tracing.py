import logging
import os

from src.config import settings
from src.initial_setup import get_logger

logger = get_logger(__name__)


def init_tracing() -> None:
    os.environ.setdefault("GOOGLE_API_KEY", settings.gemini_api_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_BASE_URL", settings.langfuse_base_url)

    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor

        GoogleADKInstrumentor().instrument()
        logger.info("GoogleADKInstrumentor activated — all ADK spans will be sent to Langfuse")
    except Exception:
        logger.warning("Failed to initialize GoogleADKInstrumentor", exc_info=True)

    try:
        from langfuse import get_client

        client = get_client()
        logger.info("Langfuse client initialized — base_url=%s", client._base_url if hasattr(client, "_base_url") else settings.langfuse_base_url)
    except Exception:
        logger.warning("Failed to initialize Langfuse client", exc_info=True)
