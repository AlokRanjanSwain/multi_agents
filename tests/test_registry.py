import tempfile
from pathlib import Path

import pytest
import yaml

from src.registry.models import AgentRegistryEntry
from src.registry.registry import AgentRegistry


@pytest.fixture
def sample_registry_data():
    return {
        "agents": [
            {
                "name": "agent_a",
                "description": "Does analysis",
                "endpoint": "/a2a/agent_a",
                "skills": ["analysis", "requirements"],
                "status": "active",
            },
            {
                "name": "agent_b",
                "description": "Does coding",
                "endpoint": "/a2a/agent_b",
                "skills": ["coding", "python"],
                "status": "active",
            },
            {
                "name": "agent_c",
                "description": "Does testing",
                "endpoint": "/a2a/agent_c",
                "skills": ["testing", "QA"],
                "status": "inactive",
            },
        ]
    }


@pytest.fixture
def registry_file(sample_registry_data, tmp_path):
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.dump(sample_registry_data, default_flow_style=False))
    return path


@pytest.fixture
def registry(registry_file):
    return AgentRegistry(registry_file)


class TestAgentRegistryLoad:
    def test_load_all_agents(self, registry):
        all_agents = registry.get_all_agents()
        assert len(all_agents) == 3

    def test_load_active_agents(self, registry):
        active = registry.get_active_agents()
        assert len(active) == 2
        assert all(a.status == "active" for a in active)

    def test_load_nonexistent_file(self, tmp_path):
        reg = AgentRegistry(tmp_path / "missing.yaml")
        assert reg.get_all_agents() == []


class TestAgentRegistryLookup:
    def test_get_by_name(self, registry):
        agent = registry.get_agent_by_name("agent_a")
        assert agent is not None
        assert agent.name == "agent_a"
        assert agent.endpoint == "/a2a/agent_a"

    def test_get_by_name_not_found(self, registry):
        assert registry.get_agent_by_name("nonexistent") is None


class TestAgentRegistrySearch:
    def test_search_by_skill_exact(self, registry):
        results = registry.search_by_skill("coding")
        assert len(results) == 1
        assert results[0].name == "agent_b"

    def test_search_by_skill_partial(self, registry):
        results = registry.search_by_skill("analy")
        assert len(results) == 1
        assert results[0].name == "agent_a"

    def test_search_by_description(self, registry):
        results = registry.search_by_skill("Does coding")
        assert len(results) == 1
        assert results[0].name == "agent_b"

    def test_search_excludes_inactive(self, registry):
        results = registry.search_by_skill("testing")
        assert len(results) == 0  # agent_c is inactive

    def test_search_case_insensitive(self, registry):
        results = registry.search_by_skill("PYTHON")
        assert len(results) == 1
        assert results[0].name == "agent_b"

    def test_search_no_results(self, registry):
        results = registry.search_by_skill("machine learning")
        assert len(results) == 0


class TestAgentRegistryMutations:
    def test_add_agent(self, registry):
        entry = AgentRegistryEntry(
            name="agent_d",
            description="New agent",
            endpoint="/a2a/agent_d",
            skills=["new_skill"],
            status="active",
        )
        registry.add_agent(entry)
        assert registry.get_agent_by_name("agent_d") is not None
        assert len(registry.get_all_agents()) == 4

    def test_add_duplicate_raises(self, registry):
        entry = AgentRegistryEntry(
            name="agent_a",
            description="Duplicate",
            endpoint="/a2a/dup",
            skills=[],
        )
        with pytest.raises(ValueError, match="already exists"):
            registry.add_agent(entry)

    def test_update_agent(self, registry):
        registry.update_agent("agent_a", description="Updated description")
        agent = registry.get_agent_by_name("agent_a")
        assert agent.description == "Updated description"

    def test_update_nonexistent_raises(self, registry):
        with pytest.raises(ValueError, match="not found"):
            registry.update_agent("missing", description="x")

    def test_remove_agent(self, registry):
        registry.remove_agent("agent_b")
        assert registry.get_agent_by_name("agent_b") is None
        assert len(registry.get_all_agents()) == 2


class TestAgentRegistryReload:
    def test_reload_picks_up_changes(self, registry, registry_file):
        # Modify the file directly
        data = yaml.safe_load(registry_file.read_text())
        data["agents"].append({
            "name": "agent_new",
            "description": "Added after load",
            "endpoint": "/a2a/agent_new",
            "skills": ["new"],
            "status": "active",
        })
        registry_file.write_text(yaml.dump(data, default_flow_style=False))

        # Reload
        registry.reload()
        assert registry.get_agent_by_name("agent_new") is not None
        assert len(registry.get_all_agents()) == 4

    def test_save_and_reload_roundtrip(self, registry, registry_file):
        entry = AgentRegistryEntry(
            name="roundtrip_agent",
            description="Test roundtrip",
            endpoint="/a2a/roundtrip",
            skills=["roundtrip"],
            status="active",
        )
        registry.add_agent(entry)

        # Create a new registry from the same file
        new_registry = AgentRegistry(registry_file)
        agent = new_registry.get_agent_by_name("roundtrip_agent")
        assert agent is not None
        assert agent.description == "Test roundtrip"
