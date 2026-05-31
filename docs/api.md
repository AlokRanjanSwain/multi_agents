# API Reference

The API server runs on **http://localhost:8000** by default.

---

## Health Check

```
GET /health
```

Returns a simple JSON confirmation that the server is running.

---

## Agent Registry

```
GET /registry
```

Returns all **active** agents from `registry.yaml`.

```
GET /registry/all
```

Returns **all** agents, including inactive ones.

### Example Response

```json
{
  "agents": [
    {
      "name": "requirements_analyst",
      "description": "Analyzes project descriptions and produces structured requirements documents...",
      "endpoint": "/a2a/requirements",
      "skills": ["requirements analysis", "user stories", "acceptance criteria"],
      "status": "active"
    }
  ]
}
```

---

## Server Logs

```
GET /logs?n=100
```

Returns the last `n` lines from the in-memory log buffer (default 100, max 500).

---

## Send a Task (SSE Streaming)

All agents accept A2A JSON-RPC 2.0 requests. Send a task to the Supervisor:

```
POST /a2a/supervisor
Content-Type: application/json
```

### Request Body

```json
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

### Response

The response is a **Server-Sent Events (SSE)** stream. Each event is a JSON object containing a status update or an artifact:

```
event: message
data: {"type": "status", "status": {"state": "working", "message": {...}}}

event: message
data: {"type": "artifact", "artifact": {"name": "requirements", "parts": [...]}}

event: message
data: {"type": "status", "status": {"state": "completed"}}
```

---

## Specialist Agent Endpoints

Each specialist agent also accepts direct A2A requests at its own endpoint:

| Agent | Endpoint |
|---|---|
| Supervisor | `POST /a2a/supervisor` |
| Requirements Analyst | `POST /a2a/requirements` |
| System Designer | `POST /a2a/designer` |
| Coder | `POST /a2a/coder` |
| Tester | `POST /a2a/tester` |
| Code Reviewer | `POST /a2a/code_reviewer` |
| DevOps Engineer | `POST /a2a/devops_engineer` |
| Security Agent | `POST /a2a/security_agent` |
