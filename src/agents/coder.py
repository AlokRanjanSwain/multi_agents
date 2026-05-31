from google.adk import Agent

from src.common.prompts import CODER_INSTRUCTION

coder_agent = Agent(
    name="coder",
    model="gemini-2.5-flash",
    description="Generates production-ready code implementations from system design specifications.",
    instruction=CODER_INSTRUCTION,
    output_key="code",
)
