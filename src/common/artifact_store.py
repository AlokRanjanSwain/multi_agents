"""
artifact_store.py — Persists agent outputs to disk, one directory per request.

Each supervisor request gets a unique request_id and a dedicated folder:
    artifacts/
    └── 20260529_143022_a1b2c3d4/
        ├── request.txt          ← task description + metadata
        ├── requirements.md      ← requirements_analyst output
        ├── design.md            ← system_designer output
        ├── code.md              ← coder output
        └── tests.md             ← tester output

Usage:
    from src.common.artifact_store import start_request, save, get_current_request_id
"""

import contextvars
import uuid
from datetime import datetime
from pathlib import Path

from src.initial_setup import get_logger

logger = get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
ARTIFACTS_DIR = Path("artifacts")

# Maps agent names to human-readable filenames
_AGENT_FILENAMES: dict[str, str] = {
    "requirements_analyst": "requirements.md",
    "system_designer": "design.md",
    "coder": "code.md",
    "tester": "tests.md",
}

# ── Per-request context variable ──────────────────────────────────────────────
# Isolated per asyncio task — two concurrent supervisor requests won't collide.
_current_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "artifact_request_id", default=None
)


# ── Public API ────────────────────────────────────────────────────────────────

def start_request(task_description: str = "") -> str:
    """Create a new artifact request directory and return the request_id.

    Should be called once per supervisor task, before any delegate_task calls.
    Sets the current context variable so save() knows which folder to use.

    Args:
        task_description: The user's original task text (written to request.txt).

    Returns:
        The generated request_id string.
    """
    request_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    request_dir = ARTIFACTS_DIR / request_id
    request_dir.mkdir(parents=True, exist_ok=True)

    (request_dir / "request.txt").write_text(
        f"Request ID : {request_id}\n"
        f"Timestamp  : {datetime.now().isoformat()}\n"
        f"Task       : {task_description}\n",
        encoding="utf-8",
    )

    _current_request_id.set(request_id)
    logger.info("Artifact request created | request_id=%s | path=%s", request_id, request_dir)
    return request_id


def get_current_request_id() -> str | None:
    """Return the request_id for the current async execution context."""
    return _current_request_id.get()


def save(agent_name: str, content: str, request_id: str | None = None) -> Path | None:
    """Persist an agent's output to the current request directory.

    Args:
        agent_name: The agent's registry name (used to pick the filename).
        content: The full text output to write.
        request_id: Override the context-var request_id (optional).

    Returns:
        Path to the written file, or None if no active request exists.
    """
    rid = request_id or _current_request_id.get()
    if rid is None:
        logger.warning("artifact_store.save called with no active request_id — skipping")
        return None

    request_dir = ARTIFACTS_DIR / rid
    request_dir.mkdir(parents=True, exist_ok=True)

    filename = _AGENT_FILENAMES.get(agent_name, f"{agent_name}.txt")
    path = request_dir / filename
    path.write_text(content, encoding="utf-8")

    logger.info(
        "Artifact saved | request_id=%s | agent=%s | file=%s | chars=%d",
        rid,
        agent_name,
        filename,
        len(content),
    )
    return path


def list_requests() -> list[dict]:
    """Return metadata for all stored artifact requests, newest first.

    Returns:
        List of dicts with keys: request_id, timestamp, task, files.
    """
    if not ARTIFACTS_DIR.exists():
        return []

    results = []
    for request_dir in sorted(ARTIFACTS_DIR.iterdir(), reverse=True):
        if not request_dir.is_dir():
            continue
        meta: dict = {"request_id": request_dir.name, "task": "", "timestamp": "", "files": []}
        manifest = request_dir / "request.txt"
        if manifest.exists():
            for line in manifest.read_text(encoding="utf-8").splitlines():
                if line.startswith("Task       :"):
                    meta["task"] = line.split(":", 1)[1].strip()
                elif line.startswith("Timestamp  :"):
                    meta["timestamp"] = line.split(":", 1)[1].strip()
        meta["files"] = [f.name for f in request_dir.iterdir() if f.name != "request.txt"]
        results.append(meta)
    return results


def load_request(request_id: str) -> dict:
    """Load all artifacts from a previous request.

    Args:
        request_id: The request_id to load (as returned by list_requests).

    Returns:
        Dict with keys: request_id, task, timestamp, and one key per artifact
        file name (without extension) mapped to its text content.
        Returns an error dict if the request_id is not found.
    """
    request_dir = ARTIFACTS_DIR / request_id
    if not request_dir.exists():
        return {"error": f"Request '{request_id}' not found in artifacts directory"}

    result: dict = {"request_id": request_id, "task": "", "timestamp": ""}

    manifest = request_dir / "request.txt"
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.startswith("Task       :"):
                result["task"] = line.split(":", 1)[1].strip()
            elif line.startswith("Timestamp  :"):
                result["timestamp"] = line.split(":", 1)[1].strip()

    for artifact_file in request_dir.iterdir():
        if artifact_file.name == "request.txt":
            continue
        key = artifact_file.stem  # e.g. "code", "requirements"
        result[key] = artifact_file.read_text(encoding="utf-8")

    logger.info("Artifact request loaded | request_id=%s | files=%s", request_id, list(result.keys()))
    return result
