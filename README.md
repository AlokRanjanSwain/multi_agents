# Multi-Agent SDLC System

A production-ready multi-agent system that automates the **Software Development Lifecycle (SDLC)** using [Google ADK](https://github.com/google/adk-python) and the [A2A (Agent-to-Agent) SDK](https://github.com/google-a2a/a2a-sdk-python). A **Supervisor** agent orchestrates four specialized agents — Requirements Analyst, System Designer, Coder, and Tester — to take a plain-language task all the way through requirements, architecture, code, and tests.

---

## Architecture

```
User / CLI
    │
    ▼
Supervisor Agent  (/a2a/supervisor)
    │  Decomposes task, delegates via A2A protocol
    ├──▶  Requirements Analyst  (/a2a/requirements)
    ├──▶  System Designer       (/a2a/designer)
    ├──▶  Coder                 (/a2a/coder)
    └──▶  Tester                (/a2a/tester)
```

All agents are built on **Gemini 2.5 Flash Lite** and communicate over the A2A protocol (JSON-RPC 2.0 + Server-Sent Events). The supervisor uses `PlanReActPlanner` for structured multi-step reasoning.

---

## Agents

| Agent | Endpoint | Responsibilities |
|---|---|---|
| **Supervisor** | `/a2a/supervisor` | Orchestrates the full SDLC pipeline; delegates to specialist agents |
| **Requirements Analyst** | `/a2a/requirements` | Produces structured requirements docs, user stories, acceptance criteria |
| **System Designer** | `/a2a/designer` | Creates architecture designs, data models, API specs |
| **Coder** | `/a2a/coder` | Generates production-ready code in Python, JavaScript, and more |
| **Tester** | `/a2a/tester` | Generates test plans, test cases, and executable test code |

Agent capabilities and routing metadata live in [`registry.yaml`](./registry.yaml) and are hot-reloaded at runtime — no restart required when adding or updating agents.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent framework | [Google ADK](https://github.com/google/adk-python) |
| Agent communication | [A2A SDK](https://github.com/google-a2a/a2a-sdk-python) |
| LLM | Gemini 2.5 Flash Lite (`google-adk`) |
| API server | FastAPI + Uvicorn |
| Observability | [Langfuse](https://langfuse.com) (tracing, prompt management) |
| Instrumentation | `openinference-instrumentation-google-adk` |
| UI | Streamlit (agent registry browser) |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```
.
├── src/
│   ├── agents/          # Agent implementations (supervisor, coder, etc.)
│   ├── common/          # Shared tools, prompts, artifact store
│   ├── registry/        # Agent registry loader & file watcher
│   ├── config.py        # Pydantic settings (loads .env)
│   ├── tracing.py       # Langfuse + ADK instrumentation setup
│   └── main.py          # FastAPI app & lifespan startup
├── ui/
│   └── registry_app.py  # Streamlit agent registry browser
├── registry.yaml        # Agent metadata (name, endpoint, skills, status)
├── run_task.py          # CLI task runner with SSE streaming output
├── docker-compose.yml           # App + Streamlit UI services
├── docker-compose.langfuse.yml  # Full Langfuse stack (Postgres, Redis, etc.)
├── Dockerfile
└── pyproject.toml
```

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2
- A **Gemini API key** — get one at [Google AI Studio](https://aistudio.google.com/app/apikey)
- Python 3.12+ and [uv](https://github.com/astral-sh/uv) *(only for local development)*

---

## Setup

### 1. Create the shared Docker network

```bash
docker network create sdlc-net
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```dotenv
# Required
GEMINI_API_KEY=your-gemini-api-key

# Langfuse (fill in after starting Langfuse — see step 3)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=http://localhost:3000
```

### 3. Start Langfuse (observability stack)

```bash
docker compose -f docker-compose.langfuse.yml up -d
```

Once healthy, open **http://localhost:3001**, create an account, create a project, and copy the **Secret Key** and **Public Key** into `.env`.

### 4. Start the application

```bash
docker compose up -d
```

Services started:

| Service | URL | Description |
|---|---|---|
| API server | http://localhost:8000 | FastAPI — all A2A agent endpoints |
| Registry UI | http://localhost:8501 | Streamlit agent registry browser |
| Langfuse | http://localhost:3001 | LLM observability dashboard |

---

## Running a Task

Use the bundled streaming CLI runner to send a task to the supervisor:

```bash
# With a task description
python run_task.py "Build a REST API for a todo app"

# Default task ("Create a clock app")
python run_task.py
```

The runner streams **status updates** and **artifact outputs** (requirements, designs, code, tests) to your terminal as the agents complete each stage.

---

## API Reference

### Health check
```
GET /health
```

### Agent registry
```
GET /registry        # Active agents only
GET /registry/all    # All agents (including inactive)
```

### Server logs (last N lines)
```
GET /logs?n=100
```

### Send a task (SSE streaming)
```
POST /a2a/supervisor
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": "<uuid>",
  "method": "message/stream",
  "params": {
    "message": {
      "role": "user",
      "parts": [{ "kind": "text", "text": "Create a clock app" }],
      "messageId": "<uuid>"
    }
  }
}
```

Each specialist agent also accepts direct A2A requests at its own endpoint (`/a2a/requirements`, `/a2a/designer`, `/a2a/coder`, `/a2a/tester`).

---

## Local Development

```bash
# Install dependencies
uv sync

# Run the API server locally
uvicorn src.main:app --reload --port 8000

# Run the Streamlit UI locally
streamlit run ui/registry_app.py --server.port 8501
```

### Running tests

```bash
uv run pytest
```

---

## Adding a New Agent

1. **Implement** the agent in `src/agents/my_agent.py` (use `src/agents/_template.py` as a guide).
2. **Register** it in `registry.yaml` with a name, description, endpoint, and skills.
3. **Wire** it into `src/main.py` — add it to `AGENT_MODULES`.
4. The registry watcher **hot-reloads** `registry.yaml` automatically; a server restart is only needed for new Python code.

---

## Observability

All LLM calls are traced via **Langfuse** using the `openinference-instrumentation-google-adk` integration. Traces include:

- Full prompt/response for every agent invocation
- Tool calls made by the supervisor
- Latency and token usage per step

Access the dashboard at **http://localhost:3001** after completing setup.
