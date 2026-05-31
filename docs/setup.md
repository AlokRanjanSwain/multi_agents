# Setup Guide

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2
- A **Gemini API key** — get one at [Google AI Studio](https://aistudio.google.com/app/apikey)
- Python 3.12+ and [uv](https://github.com/astral-sh/uv) *(only for local development)*

---

## Docker Setup (Recommended)

### 1. Clone the repository

```bash
git clone https://github.com/AlokRanjanSwain/multi_agents.git
cd multi_agents
```

### 2. Create the shared Docker network

```bash
docker network create sdlc-net
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```dotenv
# Required
GEMINI_API_KEY=your-gemini-api-key

# Langfuse (fill in after starting Langfuse — see step 4)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=http://localhost:3000
```

### 4. Start Langfuse (observability stack)

```bash
docker compose -f docker-compose.langfuse.yml up -d
```

Once healthy, open **http://localhost:3001**, create an account, create a project, and copy the **Secret Key** and **Public Key** into `.env`.

### 5. Start the application

```bash
docker compose up -d
```

### Services

| Service | URL | Description |
|---|---|---|
| API server | http://localhost:8000 | FastAPI — all A2A agent endpoints |
| Registry UI | http://localhost:8501 | Streamlit agent registry browser |
| Langfuse | http://localhost:3001 | LLM observability dashboard |

---

## Running a Task

Use the bundled streaming CLI runner to send a task to the Supervisor:

```bash
# With a task description
python run_task.py "Build a REST API for a todo app"

# Default task ("Create a clock app")
python run_task.py
```

The runner streams **status updates** and **artifact outputs** (requirements, designs, code, tests) to your terminal as each agent completes its stage.

---

## Local Development (without Docker)

### Install dependencies

```bash
uv sync
```

### Run the API server

```bash
uvicorn src.main:app --reload --port 8000
```

### Run the Streamlit UI

```bash
streamlit run ui/registry_app.py --server.port 8501
```

### Run tests

```bash
uv run pytest
```
