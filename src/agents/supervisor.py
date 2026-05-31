from google.adk import Agent
from google.adk.planners import PlanReActPlanner

from src.common.prompts import SUPERVISOR_INSTRUCTION
from src.common.tools import (
    create_artifact_request,
    delegate_task,
    get_task_status,
    list_artifact_requests,
    list_available_agents,
    load_artifact_request,
    search_agents,
)


def _handle_tool_error(tool, args, tool_context, error):
    agent_name = args.get("agent_name", "unknown") if isinstance(args, dict) else "unknown"
    return {
        "status": "error",
        "error": str(error),
        "agent": agent_name,
        "suggestion": "Search for an alternative agent with matching skills and retry, or reformulate the task.",
    }


supervisor_agent = Agent(
    name="supervisor",
    model="gemini-2.5-flash-lite",
    description="SDLC Supervisor that orchestrates software development tasks by delegating to specialized agents.",
    instruction=SUPERVISOR_INSTRUCTION,
    tools=[
        create_artifact_request,
        list_artifact_requests,
        load_artifact_request,
        list_available_agents,
        search_agents,
        delegate_task,
        get_task_status,
    ],
    planner=PlanReActPlanner(),
    on_tool_error_callback=_handle_tool_error,
    output_key="supervisor_output",
)
