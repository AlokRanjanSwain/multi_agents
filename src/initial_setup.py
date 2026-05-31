"""
initial_setup.py — Centralised logging initialisation for multi_agents.

Reads LOG_LEVEL from .env, injects it into logger.conf via ConfigParser
defaults, and exposes get_logger() for use across all modules.

Usage:
    from src.initial_setup import get_logger
    log = get_logger()
    log.info("Starting up...")

    # Or get a child logger for a specific module:
    log = get_logger(__name__)
"""

import logging
import logging.config
import os
from pathlib import Path

from dotenv import load_dotenv

# ── Load environment ──────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent          # workspace root
load_dotenv(dotenv_path=_ROOT / ".env", override=False)

# ── Constants ─────────────────────────────────────────────────────────────────
PROJECT_NAME: str = "multi_agents"
_CONF_PATH: Path = Path(__file__).parent / "logger.conf"

# ── Bootstrap ─────────────────────────────────────────────────────────────────
_initialised: bool = False


def _setup() -> None:
    """Configure logging exactly once per process."""
    global _initialised
    if _initialised:
        return

    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

    logging.config.fileConfig(
        fname=str(_CONF_PATH),
        defaults={"LOG_LEVEL": log_level},
        disable_existing_loggers=False,
    )
    _initialised = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return the project logger or a named child logger.

    Args:
        name: If None, returns the top-level project logger.
              Pass __name__ to get a dotted child,
              e.g. 'multi_agents.main'.
    """
    _setup()
    if name is None or name == PROJECT_NAME:
        return logging.getLogger(PROJECT_NAME)
    # Ensure child loggers are nested under the project namespace
    if not name.startswith(PROJECT_NAME + "."):
        name = f"{PROJECT_NAME}.{name}"
    return logging.getLogger(name)
