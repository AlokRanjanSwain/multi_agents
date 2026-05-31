"""Utilities for dynamically generating and registering new agents via LLM."""

import importlib
import json
import re
from pathlib import Path

from src.config import settings
from src.initial_setup import get_logger

logger = get_logger(__name__)

_AGENTS_DIR = Path(__file__).parent / "agents"

_SPEC_PROMPT = """\
You are a software architect designing a specialized AI agent for an SDLC multi-agent system.

Generate a complete spec for an agent with:
  Name   : {name}
  Purpose: {purpose}

Return a single JSON object — no markdown fences, no explanation — with exactly these fields:
{{
  "description": "<one clear sentence, max 200 chars>",
  "skills": ["skill1", "skill2", "skill3"],
  "instruction": "<full system prompt, 150-300 words>"
}}

Requirements for each field:
- description : concise, one sentence, no quotes inside
- skills      : 4–8 lowercase keywords relevant to the agent's domain
- instruction : address the agent in second person ("You are a …"),
                specify what inputs it receives,
                define the exact output format with numbered sections,
                be concrete and actionable
"""


def generate_agent_spec(name: str, purpose: str) -> dict:
    """Call Gemini to produce description, skills, and instruction for a new agent."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = _SPEC_PROMPT.format(name=name, purpose=purpose)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    text = response.text.strip()
    # Strip accidental markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def create_agent_file(name: str, spec: dict) -> Path:
    """Write src/agents/{name}.py from the generated spec."""
    var_name = f"{name}_agent"
    instruction_var = f"{name.upper()}_INSTRUCTION"

    # Sanitize values that will be embedded as Python string literals
    safe_instruction = spec["instruction"].replace('"""', "'''")
    safe_description = spec["description"].replace('"', '\\"')

    lines = [
        "from google.adk import Agent",
        "",
        f'{instruction_var} = """{safe_instruction}"""',
        "",
        f"{var_name} = Agent(",
        f'    name="{name}",',
        '    model="gemini-2.5-flash",',
        f'    description="{safe_description}",',
        f"    instruction={instruction_var},",
        f'    output_key="{name}_output",',
        ")",
        "",
    ]
    content = "\n".join(lines)

    path = _AGENTS_DIR / f"{name}.py"
    path.write_text(content, encoding="utf-8")
    logger.info("Created agent file: %s", path)
    return path


def load_agent_instance(name: str):
    """Dynamically import and return the agent instance from the newly created module."""
    module = importlib.import_module(f"src.agents.{name}")
    return getattr(module, f"{name}_agent")
