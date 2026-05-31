"""
Standalone script to send a task to the supervisor and stream all events to stdout.
Usage:
    python run_task.py "Create a clock app"
    python run_task.py  # uses default task below
"""

import json
import sys
import time
import uuid

import requests

BASE_URL = "http://localhost:8000"
SUPERVISOR_ENDPOINT = "/a2a/supervisor"
DEFAULT_TASK = "Create a clock app"

# ANSI colour helpers
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RED = "\033[91m"
DIM = "\033[2m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"

STATE_COLOUR = {
    "submitted": YELLOW,
    "working": CYAN,
    "completed": GREEN,
    "failed": RED,
    "canceled": DIM,
    "input-required": MAGENTA,
}


def ts() -> str:
    return time.strftime("%H:%M:%S")


def print_state(state: str) -> None:
    colour = STATE_COLOUR.get(state, RESET)
    print(f"\n{BOLD}{colour}[{ts()}] ── State: {state.upper()} ──{RESET}\n")


def print_event_header(kind: str) -> None:
    print(f"{DIM}[{ts()}] event={kind}{RESET}")


def extract_text(parts: list) -> str:
    texts = []
    for p in parts:
        if isinstance(p, dict):
            texts.append(p.get("text", ""))
    return "\n".join(t for t in texts if t).strip()


def run_task(task: str) -> None:
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}  Multi-Agent SDLC — Streaming Task Runner{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"\n{BOLD}Task:{RESET} {task}")
    print(f"{BOLD}Target:{RESET} {BASE_URL}{SUPERVISOR_ENDPOINT}")
    print(f"\n{DIM}{'─' * 70}{RESET}\n")

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/stream",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": task}],
                "messageId": str(uuid.uuid4()),
            }
        },
    }

    url = f"{BASE_URL}{SUPERVISOR_ENDPOINT}"
    final_state = "unknown"
    artifacts: list[dict] = []

    try:
        with requests.post(url, json=payload, stream=True, timeout=600) as resp:
            resp.raise_for_status()

            for raw_line in resp.iter_lines():
                if isinstance(raw_line, bytes):
                    raw_line = raw_line.decode("utf-8")
                if not raw_line.startswith("data: "):
                    continue

                try:
                    event = json.loads(raw_line[6:])
                except json.JSONDecodeError:
                    print(f"{RED}[{ts()}] Could not parse SSE line: {raw_line}{RESET}")
                    continue

                # Surface any JSON-RPC error
                if "error" in event:
                    err = event["error"]
                    print(f"{RED}[{ts()}] JSON-RPC ERROR {err.get('code')}: {err.get('message')}{RESET}")
                    if "data" in err:
                        print(f"{RED}           {err['data']}{RESET}")
                    continue

                result = event.get("result", {})
                kind = result.get("kind", "")

                # ── Initial task object ──────────────────────────────────────
                if kind == "task" or (not kind and "status" in result and "id" in result):
                    state = result.get("status", {}).get("state", "")
                    final_state = state
                    task_id = result.get("id", "?")
                    print(f"{DIM}[{ts()}] Task created  id={task_id}  state={state}{RESET}")

                # ── Status update ────────────────────────────────────────────
                elif kind == "status-update":
                    status = result.get("status", {})
                    state = status.get("state", "")
                    final_state = state
                    print_state(state)

                    msg = status.get("message", {})
                    if msg:
                        text = extract_text(msg.get("parts", []))
                        if text:
                            for line in text.splitlines():
                                print(f"  {line}")

                    if result.get("final"):
                        break

                # ── Artifact update ──────────────────────────────────────────
                elif kind == "artifact-update":
                    artifact = result.get("artifact", {})
                    name = artifact.get("name") or "output"
                    text = extract_text(artifact.get("parts", []))
                    if text:
                        artifacts.append({"name": name, "text": text})
                        print(f"\n{BOLD}{GREEN}[{ts()}] ── Artifact: {name} ──{RESET}")
                        print(text)

                # ── Unknown event ────────────────────────────────────────────
                else:
                    print(f"{DIM}[{ts()}] (raw) {json.dumps(result)[:200]}{RESET}")

    except requests.exceptions.ConnectionError:
        print(f"\n{RED}ERROR: Could not connect to {url}{RESET}")
        print("Make sure the Docker container is running: docker compose up -d")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"\n{RED}HTTP {e.response.status_code}: {e.response.text[:500]}{RESET}")
        sys.exit(1)

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    colour = STATE_COLOUR.get(final_state, RESET)
    print(f"{BOLD}{colour}  Final state: {final_state.upper()}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")

    if artifacts:
        print(f"{BOLD}Artifacts produced:{RESET}")
        for a in artifacts:
            print(f"  • {a['name']}")

    # ── Server logs ───────────────────────────────────────────────────────────
    print(f"\n{BOLD}{BLUE}{'─' * 70}{RESET}")
    print(f"{BOLD}  Last 100 server-side log lines{RESET}")
    print(f"{BOLD}{BLUE}{'─' * 70}{RESET}\n")
    try:
        log_resp = requests.get(f"{BASE_URL}/logs", params={"n": 100}, timeout=10)
        log_resp.raise_for_status()
        lines = log_resp.json().get("lines", [])
        for line in lines:
            if "ERROR" in line or "error" in line:
                print(f"{RED}{line}{RESET}")
            elif "WARNING" in line or "WARNING" in line:
                print(f"{YELLOW}{line}{RESET}")
            else:
                print(f"{DIM}{line}{RESET}")
    except Exception as exc:
        print(f"{YELLOW}Could not fetch server logs: {exc}{RESET}")


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else DEFAULT_TASK
    run_task(task)
