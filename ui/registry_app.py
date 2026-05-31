import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests
import streamlit as st
import yaml

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.registry.models import AgentRegistryEntry

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "registry.yaml"
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_registry() -> list[dict]:
    if not REGISTRY_PATH.exists():
        return []
    raw = yaml.safe_load(REGISTRY_PATH.read_text()) or {}
    return raw.get("agents", [])


def save_registry(agents: list[dict]) -> None:
    REGISTRY_PATH.write_text(
        yaml.dump({"agents": agents}, default_flow_style=False, sort_keys=False)
    )


def _extract_text_from_parts(parts: list[dict]) -> str:
    texts = []
    for p in parts:
        # 0.3.x: {"kind": "text", "text": "..."} discriminated union
        # fallback for plain dicts
        if isinstance(p, dict):
            texts.append(p.get("text", ""))
        elif hasattr(p, "root"):  # RootModel
            texts.append(getattr(p.root, "text", ""))
    return " ".join(t for t in texts if t).strip()


def _load_artifact_projects() -> list[dict]:
    """Read artifact request directories from disk, newest first."""
    if not ARTIFACTS_DIR.exists():
        return []
    projects = []
    for d in sorted(ARTIFACTS_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta = {"request_id": d.name, "task": "", "timestamp": "", "files": {}}
        manifest = d / "request.txt"
        if manifest.exists():
            for line in manifest.read_text(encoding="utf-8").splitlines():
                if line.startswith("Task       :"):
                    meta["task"] = line.split(":", 1)[1].strip()
                elif line.startswith("Timestamp  :"):
                    meta["timestamp"] = line.split(":", 1)[1].strip()
        for f in d.iterdir():
            if f.name != "request.txt" and f.suffix in (".md", ".txt"):
                meta["files"][f.stem] = f.read_text(encoding="utf-8")
        projects.append(meta)
    return projects



    colours = {
        "submitted": "🔵",
        "working": "🟡",
        "completed": "🟢",
        "failed": "🔴",
        "canceled": "⚫",
        "input-required": "🟠",
    }
    return f"{colours.get(state, '⚪')} **{state.upper()}**"


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

st.set_page_config(page_title="SDLC Multi-Agent System", page_icon="🤖", layout="wide")
st.title("SDLC Multi-Agent System")

st.sidebar.markdown("### Quick Links")
st.sidebar.markdown(f"- [App Health]({APP_BASE_URL}/health)")
st.sidebar.markdown(f"- [Registry API]({APP_BASE_URL}/registry)")
st.sidebar.markdown(f"- [Logs API]({APP_BASE_URL}/logs)")
st.sidebar.markdown("- [Langfuse Audit UI](http://localhost:3000)")
st.sidebar.markdown("---")
st.sidebar.markdown("**App URL**")
app_url = st.sidebar.text_input("Base URL", value=APP_BASE_URL, label_visibility="collapsed")

tab_registry, tab_run, tab_projects, tab_logs = st.tabs(["Registry", "Run Task", "Projects", "App Logs"])

agents = load_registry()

# ===========================================================================
# TAB 1: Registry Management
# ===========================================================================
with tab_registry:
    st.subheader("Agent Registry")
    st.caption("Changes are hot-reloaded by the running application.")

    search_query = st.text_input("Search agents by skill or name", "", key="reg_search")
    if search_query:
        q = search_query.lower()
        filtered = [
            a for a in agents
            if q in a.get("name", "").lower()
            or q in a.get("description", "").lower()
            or any(q in s.lower() for s in a.get("skills", []))
        ]
    else:
        filtered = agents

    st.markdown(f"**{len(filtered)} agent(s) shown**")

    if not filtered:
        st.info("No agents registered. Add one below.")
    else:
        for i, agent in enumerate(filtered):
            original_idx = agents.index(agent)
            status_emoji = "🟢" if agent.get("status") == "active" else "🔴"
            with st.expander(f"{status_emoji} {agent['name']} — {agent.get('description', '')[:80]}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**Endpoint:** `{agent.get('endpoint', '')}`")
                    st.markdown(f"**Skills:** {', '.join(agent.get('skills', []))}")
                    st.markdown(f"**Status:** {agent.get('status', 'active')}")
                with col2:
                    new_status = "inactive" if agent.get("status") == "active" else "active"
                    if st.button(f"Set {new_status}", key=f"toggle_{i}"):
                        agents[original_idx]["status"] = new_status
                        save_registry(agents)
                        st.rerun()
                    if st.button("Remove", key=f"delete_{i}"):
                        agents.pop(original_idx)
                        save_registry(agents)
                        st.rerun()

                st.markdown("---")
                st.markdown("**Edit:**")
                new_desc = st.text_input("Description", value=agent.get("description", ""), key=f"desc_{i}")
                new_skills = st.text_input(
                    "Skills (comma-separated)",
                    value=", ".join(agent.get("skills", [])),
                    key=f"skills_{i}",
                )
                if st.button("Save Changes", key=f"save_{i}"):
                    agents[original_idx]["description"] = new_desc
                    agents[original_idx]["skills"] = [s.strip() for s in new_skills.split(",") if s.strip()]
                    save_registry(agents)
                    st.success(f"Updated '{agent['name']}'")
                    st.rerun()

    st.markdown("---")
    st.subheader("Add New Agent")
    with st.form("add_agent_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Agent Name (unique identifier)", placeholder="code_reviewer")
            new_desc_add = st.text_input("Description", placeholder="Reviews code for quality and best practices")
            new_endpoint = st.text_input("Endpoint", placeholder="/a2a/code_reviewer")
        with col2:
            new_skills_add = st.text_input("Skills (comma-separated)", placeholder="code review, quality, best practices")
            new_status_add = st.selectbox("Status", ["active", "inactive"])

        if st.form_submit_button("Add Agent"):
            if not new_name or not new_endpoint:
                st.error("Name and endpoint are required.")
            elif any(a.get("name") == new_name for a in agents):
                st.error(f"Agent '{new_name}' already exists.")
            else:
                try:
                    entry = AgentRegistryEntry(
                        name=new_name,
                        description=new_desc_add,
                        endpoint=new_endpoint,
                        skills=[s.strip() for s in new_skills_add.split(",") if s.strip()],
                        status=new_status_add,
                    )
                    agents.append(entry.model_dump())
                    save_registry(agents)
                    st.success(f"Added agent '{new_name}'. The app will pick it up via hot-reload.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Validation error: {e}")

    st.markdown("---")
    with st.expander("✨ Auto-Generate Agent (AI-powered)", expanded=False):
        st.caption(
            "Describe what the agent should do — the AI will generate its description, "
            "skills, and system prompt, create the Python file, and register it live."
        )
        with st.form("autogen_agent_form"):
            ag_name = st.text_input(
                "Agent Name",
                placeholder="code_reviewer",
                help="snake_case identifier, e.g. code_reviewer",
            )
            ag_purpose = st.text_area(
                "Purpose / Domain",
                placeholder="Reviews Python code for bugs, style issues, and security vulnerabilities. "
                "Produces a structured review report with severity ratings.",
                height=100,
            )
            submitted = st.form_submit_button("Generate & Register", type="primary")

        if submitted:
            ag_name_clean = ag_name.strip().lower().replace("-", "_").replace(" ", "_")
            if not ag_name_clean or not ag_purpose.strip():
                st.error("Both Agent Name and Purpose are required.")
            else:
                with st.spinner(f"Generating agent '{ag_name_clean}' via Gemini…"):
                    try:
                        resp = requests.post(
                            f"{app_url}/agents/generate",
                            json={"name": ag_name_clean, "purpose": ag_purpose.strip()},
                            timeout=60,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            spec = data.get("spec", {})
                            st.success(
                                f"Agent **{data['name']}** created and mounted at `{data['endpoint']}`"
                            )
                            st.markdown(f"**Description:** {spec.get('description', '')}")
                            st.markdown(f"**Skills:** {', '.join(spec.get('skills', []))}")
                            with st.expander("System Prompt"):
                                st.text(spec.get("instruction", ""))
                            st.info("The agent is live now. `main.py` has also been patched so it persists after restart.")
                            st.rerun()
                        else:
                            detail = resp.json().get("detail", resp.text)
                            st.error(f"Error {resp.status_code}: {detail}")
                    except requests.exceptions.ConnectionError:
                        st.error(
                            f"Cannot connect to {app_url}. Make sure the app server is running."
                        )
                    except Exception as e:
                        st.error(f"Unexpected error: {e}")

# ===========================================================================
# TAB 2: Run Task
# ===========================================================================
with tab_run:
    st.subheader("Submit Task to an Agent")
    st.caption(
        "Send a task via the A2A `SendStreamingMessage` protocol and watch the live agent activity."
    )

    # Build endpoint options
    endpoint_options: dict[str, str] = {
        "Supervisor — full SDLC pipeline (plan → requirements → design → code → test)": "/a2a/supervisor"
    }
    for a in agents:
        if a.get("status") == "active" and a.get("name") != "supervisor":
            label = f"{a['name']} — {a.get('description', '')[:60]}"
            endpoint_options[label] = a["endpoint"]

    # Support prefill from Projects tab
    prefill_target = st.session_state.pop("prefill_target", None)
    prefill_task = st.session_state.pop("prefill_task", "")

    default_target_idx = 0
    if prefill_target and prefill_target in endpoint_options:
        default_target_idx = list(endpoint_options.keys()).index(prefill_target)

    target_label = st.selectbox("Target Agent", list(endpoint_options.keys()), index=default_target_idx)
    target_endpoint = endpoint_options[target_label]

    task_input = st.text_area(
        "Task Description",
        value=prefill_task,
        height=130,
        placeholder="e.g. Build a REST API for a todo-list app with CRUD operations and JWT authentication",
    )

    col_run, col_spacer = st.columns([1, 5])
    with col_run:
        run_clicked = st.button("Run Task", type="primary", disabled=not task_input.strip())

    if run_clicked and task_input.strip():
        st.markdown("---")
        st.markdown("### Live Activity")

        status_placeholder = st.empty()
        status_placeholder.markdown(_state_badge("submitted"))

        log_placeholder = st.empty()
        artifact_container = st.container()

        log_lines: list[str] = []
        artifacts: dict[str, list[str]] = {}

        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": task_input.strip()}],
                    "messageId": str(uuid.uuid4()),
                }
            },
        }

        url = f"{app_url}{target_endpoint}"
        final_state = "unknown"

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
                        continue

                    result = event.get("result", {})
                    ts = time.strftime("%H:%M:%S")
                    kind = result.get("kind", "")

                    # ── Task object (initial or final) ────────────────────────
                    if kind == "task" or (not kind and "status" in result and "id" in result):
                        state = result.get("status", {}).get("state", "")
                        final_state = state
                        task_id = result.get("id", "?")
                        log_lines.append(f"[{ts}] Task id={task_id}  state={state}")
                        status_placeholder.markdown(_state_badge(state))

                    # ── Status update event ───────────────────────────────────
                    elif kind == "status-update":
                        state = result.get("status", {}).get("state", "")
                        final_state = state
                        log_lines.append(f"[{ts}] State → {state}")
                        status_placeholder.markdown(_state_badge(state))

                        # Agent message attached to status
                        msg = result.get("status", {}).get("message", {})
                        if msg:
                            text = _extract_text_from_parts(msg.get("parts", []))
                            if text:
                                for line in text.splitlines():
                                    log_lines.append(f"[{ts}]   {line}")

                    # ── Artifact update event ─────────────────────────────────
                    elif kind == "artifact-update":
                        artifact = result.get("artifact", {})
                        name = artifact.get("name") or "output"
                        text = _extract_text_from_parts(artifact.get("parts", []))
                        if text:
                            artifacts.setdefault(name, []).append(text)
                            log_lines.append(f"[{ts}] Artifact received: {name} ({len(text)} chars)")

                    # Update the scrolling log
                    log_placeholder.text_area(
                        "Log",
                        value="\n".join(log_lines),
                        height=380,
                        disabled=True,
                        label_visibility="collapsed",
                    )

                    # Stop on final event flag or terminal state
                    if result.get("final") is True or final_state in ("completed", "failed", "canceled"):
                        break

        except requests.exceptions.ConnectionError:
            st.error(
                f"Cannot connect to {app_url}. Make sure the app server is running "
                f"(`uv run uvicorn src.main:app --port 8000`)."
            )
        except requests.exceptions.HTTPError as e:
            st.error(f"HTTP error from agent server: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")
        else:
            # Show final artifacts
            if artifacts:
                with artifact_container:
                    st.markdown("---")
                    st.markdown("### Results")
                    for name, parts in artifacts.items():
                        with st.expander(f"📄 {name}", expanded=True):
                            combined = "\n\n---\n\n".join(parts)
                            st.markdown(combined)

            # Persist to history
            st.session_state.setdefault("task_history", []).append(
                {
                    "task": task_input.strip(),
                    "target": target_label,
                    "final_state": final_state,
                    "log": list(log_lines),
                    "artifacts": {k: list(v) for k, v in artifacts.items()},
                }
            )

    # ── Task History ────────────────────────────────────────────────────────
    history: list[dict] = st.session_state.get("task_history", [])
    if history:
        st.markdown("---")
        st.subheader(f"Task History ({len(history)})")
        for idx, h in enumerate(reversed(history)):
            state_icon = "🟢" if h["final_state"] == "completed" else "🔴"
            label = f"{state_icon} #{len(history) - idx}  {h['task'][:60]}{'...' if len(h['task']) > 60 else ''}"
            with st.expander(label):
                st.caption(f"Target: {h['target']}  |  Final state: {h['final_state']}")
                st.text_area(
                    "Log",
                    value="\n".join(h["log"]),
                    height=180,
                    disabled=True,
                    key=f"hist_log_{idx}",
                    label_visibility="collapsed",
                )
                for aname, parts in h["artifacts"].items():
                    st.markdown(f"**{aname}:**")
                    st.markdown("\n\n---\n\n".join(parts))

# ===========================================================================
# TAB 3: Projects (saved artifact runs)
# ===========================================================================
with tab_projects:
    st.subheader("Previous Projects")
    st.caption("Browse all saved artifact requests. Open a project to view its outputs or send a modification task.")

    if st.button("🔄 Refresh", key="proj_refresh"):
        st.rerun()

    projects = _load_artifact_projects()

    if not projects:
        st.info("No projects yet. Run a task via the **Run Task** tab to create one.")
    else:
        st.markdown(f"**{len(projects)} project(s) found**")

        for proj in projects:
            rid = proj["request_id"]
            task_label = proj["task"] or "(no description)"
            ts_label = proj["timestamp"][:19].replace("T", " ") if proj["timestamp"] else ""
            file_names = list(proj["files"].keys())
            header = f"📁 `{rid}`  —  {task_label[:70]}{'...' if len(task_label) > 70 else ''}"

            with st.expander(header):
                col_meta, col_action = st.columns([3, 1])
                with col_meta:
                    st.caption(f"**Timestamp:** {ts_label}  |  **Files:** {', '.join(file_names) or 'none'}")

                with col_action:
                    if st.button("✏️ Modify this project", key=f"mod_{rid}"):
                        st.session_state["prefill_task"] = (
                            f"Modify project {rid}: [describe your changes here]\n\n"
                            f"Original task: {task_label}"
                        )
                        st.session_state["prefill_target"] = "Supervisor — full SDLC pipeline (plan → requirements → design → code → test)"
                        st.info("Prefilled in **Run Task** tab. Switch to that tab to submit.")

                # Show each artifact file in its own sub-tab
                if proj["files"]:
                    FILE_ORDER = ["requirements", "design", "code", "tests"]
                    ordered = [k for k in FILE_ORDER if k in proj["files"]]
                    ordered += [k for k in proj["files"] if k not in FILE_ORDER]

                    artifact_tabs = st.tabs([f"📄 {k}" for k in ordered])
                    for tab, key in zip(artifact_tabs, ordered):
                        with tab:
                            content = proj["files"][key]
                            st.markdown(content)
                            st.download_button(
                                label=f"⬇ Download {key}",
                                data=content,
                                file_name=f"{rid}_{key}.md",
                                mime="text/markdown",
                                key=f"dl_{rid}_{key}",
                            )
                else:
                    st.info("No artifact files saved for this request yet.")

# ===========================================================================
# TAB 4: App Logs
# ===========================================================================
with tab_logs:
    st.subheader("Application Logs")
    st.caption(f"Tailing the last N lines from `{app_url}/logs`.")

    col_n, col_refresh, col_auto = st.columns([1, 1, 2])
    with col_n:
        log_n = st.number_input("Lines", min_value=10, max_value=500, value=100, step=10)
    with col_refresh:
        st.markdown("<br/>", unsafe_allow_html=True)
        refresh = st.button("Refresh")
    with col_auto:
        st.markdown("<br/>", unsafe_allow_html=True)
        auto_refresh = st.checkbox("Auto-refresh every 5s", value=False)

    logs_text = ""
    try:
        resp = requests.get(f"{app_url}/logs", params={"n": log_n}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        lines = data.get("lines", [])
        logs_text = "\n".join(lines) if lines else "(no log lines yet)"
    except requests.exceptions.ConnectionError:
        logs_text = f"Cannot connect to {app_url}. Start the app server first."
    except Exception as e:
        logs_text = f"Error fetching logs: {e}"

    st.text_area(
        "Server logs",
        value=logs_text,
        height=520,
        disabled=True,
        label_visibility="collapsed",
    )

    if auto_refresh:
        time.sleep(5)
        st.rerun()

