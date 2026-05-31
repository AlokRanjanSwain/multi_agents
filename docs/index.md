# Multi-Agent SDLC System

A production-ready multi-agent system that automates the **Software Development Lifecycle (SDLC)** using [Google ADK](https://github.com/google/adk-python) and the [A2A (Agent-to-Agent) SDK](https://github.com/google-a2a/a2a-sdk-python).

A **Supervisor** agent orchestrates specialized agents — Requirements Analyst, System Designer, Coder, Tester, Code Reviewer, DevOps Engineer, and Security Agent — to take a plain-language task all the way through requirements, architecture, code, and tests.

---

## Key Features

- **Full SDLC automation** — from a plain-language task description to requirements, architecture, code, and tests
- **Agent-to-Agent (A2A) protocol** — agents communicate via JSON-RPC 2.0 + Server-Sent Events for real-time streaming
- **Hot-reloadable registry** — add or update agents in `registry.yaml` without restarting the server
- **Built-in observability** — Langfuse tracing and prompt management out of the box
- **Docker-first** — production-ready `docker-compose.yml` gets the full stack running in one command
- **Streamlit UI** — live registry browser to inspect agent status, skills, and endpoints

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent framework | [Google ADK](https://github.com/google/adk-python) |
| Agent communication | [A2A SDK](https://github.com/google-a2a/a2a-sdk-python) |
| LLM | Gemini 2.5 Flash Lite |
| API server | FastAPI + Uvicorn |
| Observability | [Langfuse](https://langfuse.com) |
| Instrumentation | `openinference-instrumentation-google-adk` |
| UI | Streamlit |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| Containerisation | Docker + Docker Compose |

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/AlokRanjanSwain/multi_agents.git
cd multi_agents

# 2. Create the shared Docker network
docker network create sdlc-net

# 3. Copy and configure environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 4. Start the application
docker compose up -d

# 5. Run your first task
python run_task.py "Build a REST API for a todo app"
```

See the [Setup Guide](setup.md) for full instructions including Langfuse observability.
