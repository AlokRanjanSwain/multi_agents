from google.adk import Agent

from src.common.prompts import REQUIREMENTS_ANALYST_INSTRUCTION

requirements_analyst_agent = Agent(
    name="requirements_analyst",
    model="gemini-2.5-flash-lite",
    description="Analyzes project descriptions and produces structured requirements documents with user stories, acceptance criteria, and constraints.",
    instruction=REQUIREMENTS_ANALYST_INSTRUCTION,
    output_key="requirements",
)
