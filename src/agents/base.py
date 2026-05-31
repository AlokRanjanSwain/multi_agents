import logging

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotificationConfigStore, InMemoryTaskStore
from a2a.types import AgentCapabilities
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
from google.adk.agents.base_agent import BaseAgent
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from src.initial_setup import get_logger

logger = get_logger(__name__)


def _create_runner(agent: BaseAgent) -> Runner:
    return Runner(
        app_name=agent.name or "adk_agent",
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
        credential_service=InMemoryCredentialService(),
    )


async def create_a2a_routes(
    agent: BaseAgent,
    route_prefix: str,
    host: str = "localhost",
    port: int = 8000,
) -> list:
    runner = _create_runner(agent)
    task_store = InMemoryTaskStore()
    push_config_store = InMemoryPushNotificationConfigStore()

    agent_executor = A2aAgentExecutor(runner=runner)

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=task_store,
        push_config_store=push_config_store,
    )

    # Build agent card with streaming enabled
    rpc_url = f"http://{host}:{port}{route_prefix}"
    card_builder = AgentCardBuilder(
        agent=agent,
        rpc_url=rpc_url,
        capabilities=AgentCapabilities(streaming=True),
    )
    agent_card = await card_builder.build()

    # Create the A2A Starlette application and extract routes with the prefix
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    # Mount the RPC POST endpoint and agent card GET endpoints at the prefix
    routes = a2a_app.routes(
        rpc_url=route_prefix,
        agent_card_url=f"{route_prefix}/.well-known/agent-card.json",
        extended_agent_card_url=f"{route_prefix}/agent/authenticatedExtendedCard",
    )
    return routes

