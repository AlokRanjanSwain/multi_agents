from google.adk import Agent

from src.common.prompts import SYSTEM_DESIGNER_INSTRUCTION

system_designer_agent = Agent(
    name="system_designer",
    model="gemini-2.5-flash-lite",
    description="Creates system architecture designs, component diagrams, data models, and API specifications from requirements.",
    instruction=SYSTEM_DESIGNER_INSTRUCTION,
    output_key="design",
)
