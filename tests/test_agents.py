import pytest
from unittest.mock import AsyncMock, patch

from src.agents.requirements_analyst import requirements_analyst_agent
from src.agents.system_designer import system_designer_agent
from src.agents.coder import coder_agent
from src.agents.tester import tester_agent
from src.agents.supervisor import supervisor_agent


class TestAgentDefinitions:
    """Verify all agents are properly defined with required attributes."""

    @pytest.mark.parametrize(
        "agent,expected_name",
        [
            (requirements_analyst_agent, "requirements_analyst"),
            (system_designer_agent, "system_designer"),
            (coder_agent, "coder"),
            (tester_agent, "tester"),
            (supervisor_agent, "supervisor"),
        ],
    )
    def test_agent_has_name(self, agent, expected_name):
        assert agent.name == expected_name

    @pytest.mark.parametrize(
        "agent",
        [
            requirements_analyst_agent,
            system_designer_agent,
            coder_agent,
            tester_agent,
            supervisor_agent,
        ],
    )
    def test_agent_has_description(self, agent):
        assert agent.description is not None
        assert len(agent.description) > 10

    @pytest.mark.parametrize(
        "agent",
        [
            requirements_analyst_agent,
            system_designer_agent,
            coder_agent,
            tester_agent,
            supervisor_agent,
        ],
    )
    def test_agent_has_model(self, agent):
        assert agent.model is not None

    @pytest.mark.parametrize(
        "agent,expected_key",
        [
            (requirements_analyst_agent, "requirements"),
            (system_designer_agent, "design"),
            (coder_agent, "code"),
            (tester_agent, "tests"),
            (supervisor_agent, "supervisor_output"),
        ],
    )
    def test_agent_has_output_key(self, agent, expected_key):
        assert agent.output_key == expected_key


class TestSupervisorTools:
    def test_supervisor_has_tools(self):
        assert supervisor_agent.tools is not None
        assert len(supervisor_agent.tools) == 4

    def test_supervisor_has_planner(self):
        assert supervisor_agent.planner is not None

    def test_supervisor_has_error_callback(self):
        assert supervisor_agent.on_tool_error_callback is not None


class TestToolFunctions:
    def test_list_available_agents_no_registry(self):
        from src.common.tools import list_available_agents, _registry
        import src.common.tools as tools_module
        original = tools_module._registry
        tools_module._registry = None
        result = list_available_agents()
        assert "error" in result
        tools_module._registry = original

    def test_search_agents_no_registry(self):
        from src.common.tools import search_agents
        import src.common.tools as tools_module
        original = tools_module._registry
        tools_module._registry = None
        result = search_agents("test")
        assert "error" in result
        tools_module._registry = original

    def test_list_available_agents_with_registry(self, tmp_path):
        import yaml
        from src.common.tools import list_available_agents, set_registry
        from src.registry.registry import AgentRegistry

        path = tmp_path / "reg.yaml"
        path.write_text(yaml.dump({"agents": [
            {"name": "test_agent", "description": "Test", "endpoint": "/a2a/test", "skills": ["testing"], "status": "active"}
        ]}))
        reg = AgentRegistry(path)
        set_registry(reg)
        result = list_available_agents()
        assert len(result["agents"]) == 1
        assert result["agents"][0]["name"] == "test_agent"

    def test_search_agents_with_registry(self, tmp_path):
        import yaml
        from src.common.tools import search_agents, set_registry
        from src.registry.registry import AgentRegistry

        path = tmp_path / "reg.yaml"
        path.write_text(yaml.dump({"agents": [
            {"name": "coder", "description": "Writes code", "endpoint": "/a2a/coder", "skills": ["coding", "python"], "status": "active"},
            {"name": "tester", "description": "Tests code", "endpoint": "/a2a/tester", "skills": ["testing"], "status": "active"},
        ]}))
        reg = AgentRegistry(path)
        set_registry(reg)
        result = search_agents("coding")
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "coder"
