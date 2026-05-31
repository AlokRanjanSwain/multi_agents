import logging
from typing import Any

import httpx

from src.common import artifact_store
from src.initial_setup import get_logger
from src.registry.registry import AgentRegistry

logger = get_logger(__name__)

# Global registry reference — set by main.py at startup
_registry: AgentRegistry | None = None
_app_base_url: str = "http://localhost:8000"


def set_registry(registry: AgentRegistry, base_url: str = "http://localhost:8000") -> None:
    global _registry, _app_base_url
    _registry = registry
    _app_base_url = base_url


def create_artifact_request(task_description: str) -> dict[str, Any]:
    """Create a new artifact request directory for this task run.

    Must be called ONCE at the start of every task, before any delegate_task calls.
    Returns a request_id and the path where all agent outputs will be saved.

    Args:
        task_description: The user's original task description.
    """
    request_id = artifact_store.start_request(task_description)
    path = str(artifact_store.ARTIFACTS_DIR / request_id)
    return {
        "request_id": request_id,
        "artifacts_path": path,
        "message": f"Artifact directory created at {path}. All agent outputs will be saved here.",
    }


def list_artifact_requests() -> dict[str, Any]:
    """List all previous artifact requests (completed task runs) stored on disk.

    Use this when the user asks to modify or continue a previous project.
    Returns request_id, original task description, timestamp, and saved files for each.
    """
    requests = artifact_store.list_requests()
    return {"total": len(requests), "requests": requests}


def load_artifact_request(request_id: str) -> dict[str, Any]:
    """Load all saved artifacts from a previous request by its request_id.

    Returns the original task, timestamp, and the full text of each saved artifact
    (requirements, design, code, tests). Use the content as context when delegating
    modification tasks to agents.

    Args:
        request_id: The request_id from list_artifact_requests.
    """
    return artifact_store.load_request(request_id)


def list_available_agents() -> dict[str, Any]:
    """List all active agents in the registry with their names, descriptions, skills, and endpoints."""
    if _registry is None:
        return {"error": "Registry not initialized"}
    agents = _registry.get_active_agents()
    return {
        "agents": [
            {
                "name": a.name,
                "description": a.description,
                "skills": a.skills,
                "endpoint": a.endpoint,
            }
            for a in agents
        ]
    }


def search_agents(query: str) -> dict[str, Any]:
    """Search for agents by skill keyword. Returns agents whose skills or description match the query.

    Args:
        query: A keyword to search for in agent skills and descriptions.
    """
    if _registry is None:
        return {"error": "Registry not initialized"}
    agents = _registry.search_by_skill(query)
    return {
        "query": query,
        "results": [
            {
                "name": a.name,
                "description": a.description,
                "skills": a.skills,
                "endpoint": a.endpoint,
            }
            for a in agents
        ],
    }


async def delegate_task(agent_name: str, task_description: str) -> dict[str, Any]:
    """Delegate a task to a specific agent by sending an A2A message.

    The agent must be active in the registry. The task description should include
    all relevant context needed for the agent to complete its work.

    Args:
        agent_name: The name of the agent to delegate to (must be in registry).
        task_description: A detailed description of the task including all context.
    """
    if _registry is None:
        return {"error": "Registry not initialized", "agent": agent_name}

    agent_entry = _registry.get_agent_by_name(agent_name)
    if agent_entry is None:
        return {"error": f"Agent '{agent_name}' not found in registry", "agent": agent_name}
    if agent_entry.status != "active":
        return {"error": f"Agent '{agent_name}' is inactive", "agent": agent_name}

    endpoint = f"{_app_base_url}{agent_entry.endpoint}"

    payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "id": f"delegate-{agent_name}",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": task_description}],
                "messageId": f"msg-{agent_name}",
            }
        },
    }

    logger.info("Agent [%s] → STARTED | endpoint=%s", agent_name, endpoint)
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            result = response.json()

        if "error" in result:
            err = result["error"]
            logger.error(
                "Agent [%s] → FAILED | code=%s message=%s",
                agent_name,
                err.get("code", "?"),
                err.get("message", err),
            )
            return {
                "status": "error",
                "agent": agent_name,
                "error": err,
            }

        task_result = result.get("result", {})
        # Extract text from artifacts or messages
        output_text = _extract_text_from_a2a_response(task_result)

        # Truncate very large outputs to avoid bloating the supervisor's context
        # and triggering MAX_TOKENS on the next LLM call.
        MAX_OUTPUT_CHARS = 8000
        if len(output_text) > MAX_OUTPUT_CHARS:
            output_text = output_text[:MAX_OUTPUT_CHARS] + f"\n\n[...output truncated at {MAX_OUTPUT_CHARS} chars — full result stored in agent session]"

        saved_path = artifact_store.save(agent_name, output_text)
        logger.info(
            "Agent [%s] → COMPLETED | output_chars=%d | artifact=%s",
            agent_name,
            len(output_text),
            saved_path or "(no active request)",
        )
        return {
            "status": "success",
            "agent": agent_name,
            "output": output_text,
        }
    except httpx.HTTPStatusError as e:
        logger.error(
            "Agent [%s] → FAILED | HTTP %d: %s",
            agent_name,
            e.response.status_code,
            e.response.text[:200],
        )
        return {
            "status": "error",
            "agent": agent_name,
            "error": f"HTTP {e.response.status_code}: {e.response.text[:500]}",
        }
    except Exception as e:
        logger.error("Agent [%s] → FAILED | %s: %s", agent_name, type(e).__name__, e)
        return {
            "status": "error",
            "agent": agent_name,
            "error": str(e),
        }


async def get_task_status(task_id: str, agent_name: str) -> dict[str, Any]:
    """Check the status of a previously delegated task.

    Args:
        task_id: The task ID returned from a previous delegation.
        agent_name: The name of the agent the task was delegated to.
    """
    if _registry is None:
        return {"error": "Registry not initialized"}

    agent_entry = _registry.get_agent_by_name(agent_name)
    if agent_entry is None:
        return {"error": f"Agent '{agent_name}' not found"}

    endpoint = f"{_app_base_url}{agent_entry.endpoint}"

    payload = {
        "jsonrpc": "2.0",
        "method": "tasks/get",
        "id": f"status-{task_id}",
        "params": {"id": task_id},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            result = response.json()
        return {"task_id": task_id, "agent": agent_name, "result": result.get("result", {})}
    except Exception as e:
        return {"error": str(e), "task_id": task_id, "agent": agent_name}


def _extract_text_from_a2a_response(result: dict) -> str:
    """Extract readable text from an A2A task/message response."""
    parts_sources = []

    # Check for direct message response
    if "parts" in result:
        parts_sources.append(result["parts"])

    # Check for task with artifacts
    for artifact in result.get("artifacts", []):
        if "parts" in artifact:
            parts_sources.append(artifact["parts"])

    # Check for task with history/messages
    for message in result.get("history", []):
        if message.get("role") == "agent" and "parts" in message:
            parts_sources.append(message["parts"])

    texts = []
    for parts in parts_sources:
        for part in parts:
            if isinstance(part, dict):
                if "text" in part:
                    texts.append(part["text"])
                elif part.get("kind") == "text" and "text" in part:
                    texts.append(part["text"])

    return "\n\n".join(texts) if texts else str(result)
