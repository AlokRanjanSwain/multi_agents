import collections
import logging
import warnings
from contextlib import asynccontextmanager

# Suppress noisy [EXPERIMENTAL] UserWarnings from google-adk A2A internals
warnings.filterwarnings("ignore", message=r"\[EXPERIMENTAL\]", category=UserWarning)

from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from pydantic import BaseModel
from starlette.routing import Route

from src.agents.base import create_a2a_routes
from src.agents.coder import coder_agent
from src.agents.requirements_analyst import requirements_analyst_agent
from src.agents.supervisor import supervisor_agent
from src.agents.system_designer import system_designer_agent
from src.agents.tester import tester_agent
from src.agents.code_reviewer import code_reviewer_agent
from src.agents.devops_engineer import devops_engineer_agent
from src.common.tools import set_registry
from src.config import settings
from src.initial_setup import get_logger
from src.registry.registry import AgentRegistry
from src.registry.watcher import start_registry_watcher
from src.tracing import init_tracing

logger = get_logger(__name__)

# In-memory log buffer — last 500 lines, exposed via /logs
_log_buffer: collections.deque = collections.deque(maxlen=500)


class _BufferHandler(logging.Handler):
    """Appends formatted log records to the in-memory buffer."""

    def emit(self, record: logging.LogRecord) -> None:
        _log_buffer.append(self.format(record))


_buf_handler = _BufferHandler()
_buf_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
logging.getLogger("multi_agents").addHandler(_buf_handler)

# Agent name → agent instance mapping
AGENT_MODULES = {
    "requirements_analyst": requirements_analyst_agent,
    "system_designer": system_designer_agent,
    "coder": coder_agent,
    "tester": tester_agent,
    "code_reviewer": code_reviewer_agent,
    "devops_engineer": devops_engineer_agent,
}

registry: AgentRegistry | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global registry

    # 1. Initialize tracing (Langfuse + ADK instrumentation)
    init_tracing()

    # 2. Load agent registry
    registry = AgentRegistry(settings.registry_path)
    set_registry(registry, f"http://localhost:{settings.app_port}")

    # 3. Start file watcher for hot-reload
    observer = start_registry_watcher(registry, settings.registry_path)

    # 4. Mount A2A routes for each registered agent
    for entry in registry.get_all_agents():
        agent_instance = AGENT_MODULES.get(entry.name)
        if agent_instance is None:
            logger.warning("No agent implementation for '%s' — skipping", entry.name)
            continue
        try:
            routes = await create_a2a_routes(
                agent=agent_instance,
                route_prefix=entry.endpoint,
                host=settings.app_host,
                port=settings.app_port,
            )
            for route in routes:
                app.routes.append(route)
            logger.info("Mounted agent '%s' at %s", entry.name, entry.endpoint)
        except Exception:
            logger.error("Failed to mount agent '%s'", entry.name, exc_info=True)

    # 5. Mount supervisor
    try:
        supervisor_routes = await create_a2a_routes(
            agent=supervisor_agent,
            route_prefix="/a2a/supervisor",
            host=settings.app_host,
            port=settings.app_port,
        )
        for route in supervisor_routes:
            app.routes.append(route)
        logger.info("Mounted supervisor at /a2a/supervisor")
    except Exception:
        logger.error("Failed to mount supervisor", exc_info=True)

    logger.info("Multi-Agent SDLC System started — %d agents registered", len(registry.get_active_agents()))
    yield

    # Shutdown
    observer.stop()
    observer.join()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Multi-Agent SDLC System",
    description="A2A + Google ADK multi-agent system for software development lifecycle",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/registry")
async def get_registry():
    if registry is None:
        return {"agents": []}
    agents = registry.get_active_agents()
    return {
        "agents": [
            {
                "name": a.name,
                "description": a.description,
                "endpoint": a.endpoint,
                "skills": a.skills,
                "status": a.status,
            }
            for a in agents
        ]
    }


@app.get("/registry/all")
async def get_all_registry():
    if registry is None:
        return {"agents": []}
    agents = registry.get_all_agents()
    return {
        "agents": [
            {
                "name": a.name,
                "description": a.description,
                "endpoint": a.endpoint,
                "skills": a.skills,
                "status": a.status,
            }
            for a in agents
        ]
    }


@app.get("/logs")
async def get_logs(n: int = Query(default=200, ge=1, le=500)):
    """Return the last n lines from the in-memory log buffer."""
    lines = list(_log_buffer)[-n:]
    return {"lines": lines, "total": len(lines)}


class GenerateAgentRequest(BaseModel):
    name: str
    purpose: str


@app.post("/agents/generate", tags=["Agent Management"])
async def generate_agent(body: GenerateAgentRequest, req: Request):
    """LLM-generate a new agent, write its file, update the registry, and mount its routes live."""
    from src.agent_factory import (
        create_agent_file,
        generate_agent_spec,
        load_agent_instance,
        patch_main_py,
    )
    from src.registry.models import AgentRegistryEntry

    name = body.name.strip().lower().replace("-", "_").replace(" ", "_")

    if not name.isidentifier():
        raise HTTPException(status_code=400, detail=f"'{name}' is not a valid Python identifier")

    if Path(f"src/agents/{name}.py").exists():
        raise HTTPException(status_code=409, detail=f"Agent '{name}' already exists")

    if registry and registry.get_agent_by_name(name):
        raise HTTPException(status_code=409, detail=f"Agent '{name}' is already registered")

    # 1. Generate spec via LLM
    spec = generate_agent_spec(name, body.purpose)

    # 2. Write agent Python file
    create_agent_file(name, spec)

    # 3. Patch main.py so the agent survives server restarts
    patch_main_py(name)

    # 4. Register in registry (saves registry.yaml)
    entry = AgentRegistryEntry(
        name=name,
        description=spec["description"],
        endpoint=f"/a2a/{name}",
        skills=spec["skills"],
        status="active",
    )
    registry.add_agent(entry)

    # 5. Dynamically load and mount A2A routes without restart
    agent_instance = load_agent_instance(name)
    routes = await create_a2a_routes(
        agent=agent_instance,
        route_prefix=entry.endpoint,
        host=settings.app_host,
        port=settings.app_port,
    )
    for route in routes:
        req.app.routes.append(route)

    logger.info("Dynamically mounted agent '%s' at %s", name, entry.endpoint)
    return {
        "status": "created",
        "name": name,
        "endpoint": entry.endpoint,
        "spec": spec,
    }
