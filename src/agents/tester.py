from google.adk import Agent

from src.common.prompts import TESTER_INSTRUCTION

tester_agent = Agent(
    name="tester",
    model="gemini-2.5-flash-lite",
    description="Generates test plans, test cases, and executable test code from requirements and source code.",
    instruction=TESTER_INSTRUCTION,
    output_key="tests",
)
