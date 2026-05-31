from pydantic import BaseModel


class AgentRegistryEntry(BaseModel):
    name: str
    description: str
    endpoint: str
    skills: list[str] = []
    status: str = "active"
