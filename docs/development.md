# Development Guide

## Local Setup

```bash
# Clone the repo
git clone https://github.com/AlokRanjanSwain/multi_agents.git
cd multi_agents

# Install all dependencies (including dev)
uv sync

# Run the API server with hot-reload
uvicorn src.main:app --reload --port 8000

# Run the Streamlit UI
streamlit run ui/registry_app.py --server.port 8501
```

---

## Running Tests

```bash
uv run pytest
```

---

## Adding a New Agent

### 1. Create the agent module

Copy `src/agents/_template.py` to `src/agents/my_agent.py` and implement your agent:

```python
from google.adk.agents import LlmAgent
from src.common.tools import get_shared_tools
from src.initial_setup import get_logger

logger = get_logger(__name__)

my_agent_agent = LlmAgent(
    name="my_agent",
    model="gemini-2.5-flash-lite",
    instruction="""
    You are a specialist agent. Your task is to...
    """,
    tools=get_shared_tools(),
)
```

!!! note
    The variable name must follow the pattern `{agent_name}_agent` to be auto-discovered by `main.py`.

### 2. Register in `registry.yaml`

```yaml
agents:
  - name: my_agent
    description: Short description of what this agent does.
    endpoint: /a2a/my_agent
    skills:
      - skill one
      - skill two
    status: active
```

The registry watcher will **hot-reload** this change immediately — no server restart needed.

### 3. Wire into `main.py`

Add your module name to the `AGENT_MODULES` list in `src/main.py`:

```python
AGENT_MODULES = [
    "requirements_analyst",
    "system_designer",
    "coder",
    "tester",
    "code_reviewer",
    "devops_engineer",
    "security_agent",
    "my_agent",   # <-- add this
]
```

Restart the server to pick up the new Python module.

---

## Hot-Reloading the Registry

`registry.yaml` is watched by a `watchdog` file observer. Any save to the file triggers an automatic in-memory reload of agent metadata. This means:

- Changing an agent's `status`, `description`, or `skills` takes effect immediately.
- Adding a new agent entry to `registry.yaml` is reflected instantly in `/registry` and the Streamlit UI.
- A server restart is **only** needed when new Python agent code is added.

---

## Project Conventions

| Convention | Detail |
|---|---|
| Agent variable naming | `{agent_name}_agent` in `src/agents/{agent_name}.py` |
| Settings | Pydantic `BaseSettings` in `src/config.py`, loaded from `.env` |
| Logging | Named loggers via `src/initial_setup.get_logger(__name__)` |
| Tracing | Langfuse spans auto-captured via `openinference` instrumentation |
| Packaging | `uv` with `pyproject.toml`; Docker for production |
