"""
Agent Template — Copy this file to create a new SDLC agent.

Steps to add a new agent:
1. Copy this file: cp _template.py my_agent.py
2. Rename the agent variable and update name, description, instruction, skills.
3. Add the agent to registry.yaml:
       - name: my_agent
         description: "What this agent does"
         endpoint: /a2a/my_agent
         skills: [skill_a, skill_b]
         status: active
4. Import and register the agent in src/main.py:
       from src.agents.my_agent import my_agent_agent
       Add to AGENT_MODULES dict.
5. Restart the application (registry changes hot-reload, but new code requires restart).
"""

from google.adk import Agent

# TODO: Update the instruction with your agent's specific expertise
MY_AGENT_INSTRUCTION = """You are a specialized agent for [DOMAIN].

Given [INPUT], you MUST produce [OUTPUT] containing:

1. [Section 1]
2. [Section 2]
3. [Section 3]

Be thorough, clear, and structured in your response.
"""

# TODO: Rename this variable and update all fields
template_agent = Agent(
    name="template_agent",  # Must match registry.yaml name
    model="gemini-2.5-flash",
    description="A template agent — update this description.",
    instruction=MY_AGENT_INSTRUCTION,
    output_key="template_output",  # State key for this agent's output
    # tools=[],  # Add tools if needed
)
