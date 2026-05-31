import logging
import threading
from pathlib import Path

import yaml

from src.initial_setup import get_logger
from src.registry.models import AgentRegistryEntry

logger = get_logger(__name__)


class AgentRegistry:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._agents: list[AgentRegistryEntry] = []
        self._lock = threading.RLock()
        self.load()

    def load(self) -> None:
        with self._lock:
            if not self._path.exists():
                logger.warning("Registry file not found: %s", self._path)
                self._agents = []
                return
            raw = yaml.safe_load(self._path.read_text()) or {}
            entries = raw.get("agents", [])
            self._agents = [AgentRegistryEntry(**e) for e in entries]
            logger.info(
                "Loaded %d agents from %s (%d active)",
                len(self._agents),
                self._path,
                len(self.get_active_agents()),
            )

    def reload(self) -> None:
        logger.info("Reloading agent registry from %s", self._path)
        self.load()

    def get_all_agents(self) -> list[AgentRegistryEntry]:
        with self._lock:
            return list(self._agents)

    def get_active_agents(self) -> list[AgentRegistryEntry]:
        with self._lock:
            return [a for a in self._agents if a.status == "active"]

    def get_agent_by_name(self, name: str) -> AgentRegistryEntry | None:
        with self._lock:
            return next((a for a in self._agents if a.name == name), None)

    def search_by_skill(self, query: str) -> list[AgentRegistryEntry]:
        query_lower = query.lower()
        with self._lock:
            results = []
            for agent in self._agents:
                if agent.status != "active":
                    continue
                if any(query_lower in s.lower() for s in agent.skills):
                    results.append(agent)
                elif query_lower in agent.description.lower():
                    results.append(agent)
                elif query_lower in agent.name.lower():
                    results.append(agent)
            return results

    def save(self) -> None:
        with self._lock:
            data = {"agents": [a.model_dump() for a in self._agents]}
            self._path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
            logger.info("Saved %d agents to %s", len(self._agents), self._path)

    def add_agent(self, entry: AgentRegistryEntry) -> None:
        with self._lock:
            if any(a.name == entry.name for a in self._agents):
                raise ValueError(f"Agent '{entry.name}' already exists")
            self._agents.append(entry)
        self.save()

    def update_agent(self, name: str, **kwargs) -> None:
        with self._lock:
            agent = next((a for a in self._agents if a.name == name), None)
            if not agent:
                raise ValueError(f"Agent '{name}' not found")
            for key, value in kwargs.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
        self.save()

    def remove_agent(self, name: str) -> None:
        with self._lock:
            self._agents = [a for a in self._agents if a.name != name]
        self.save()
