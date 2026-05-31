# Agents

All agents are built on **Gemini 2.5 Flash Lite** via Google ADK and communicate over the A2A protocol (JSON-RPC 2.0 + SSE).

Agent metadata (endpoint, skills, status) is managed in [`registry.yaml`](https://github.com/AlokRanjanSwain/multi_agents/blob/main/registry.yaml) and hot-reloaded at runtime.

---

## Supervisor

**Endpoint:** `/a2a/supervisor`

The Supervisor is the entry point for all tasks. It uses `PlanReActPlanner` for structured multi-step reasoning — it decomposes a task, delegates to the appropriate specialist agents in sequence, and assembles the final output.

**Skills:** task orchestration, SDLC planning, multi-agent delegation

---

## Requirements Analyst

**Endpoint:** `/a2a/requirements`

Analyzes project descriptions and produces structured requirements documents with user stories, acceptance criteria, and constraints. Handles feature requests, system analysis, and business requirements for any type of software project.

**Skills:**

- Requirements analysis
- User stories
- Acceptance criteria
- Business analysis
- Feature specification
- Project scoping

---

## System Designer

**Endpoint:** `/a2a/designer`

Creates system architecture designs, component diagrams, data models, and API specifications from requirements.

**Skills:**

- System design
- Architecture
- Data modeling
- API design
- Component design

---

## Coder

**Endpoint:** `/a2a/coder`

Generates production-ready code implementations in Python, JavaScript, and other languages. Builds REST APIs, web apps, CLI tools, scripts, and full-stack applications from design specifications.

**Skills:**

- Code generation
- Python, JavaScript
- REST API development
- Backend & full-stack development
- CLI tools

---

## Tester

**Endpoint:** `/a2a/tester`

Generates test plans, test cases, and executable test code from requirements and source code.

**Skills:**

- Test planning
- Test case generation
- Test automation
- QA & quality assurance

---

## Code Reviewer

**Endpoint:** `/a2a/code_reviewer`

Reviews Python code for bugs, quality, and security issues, producing structured reports with severity levels and fix suggestions.

**Skills:**

- Code analysis & static analysis
- Bug detection
- Security review
- Code quality & Python linting
- Vulnerability assessment

---

## DevOps Engineer

**Endpoint:** `/a2a/devops_engineer`

Manages cloud infrastructure, automates deployments, and maintains CI/CD pipelines to ensure application reliability and efficient delivery.

**Skills:**

- Cloud management
- CI/CD pipelines
- Deployment automation
- Infrastructure as Code
- Monitoring & containerization

---

## Security Agent

**Endpoint:** `/a2a/security_agent`

Specializes in identifying, analyzing, and reporting security vulnerabilities within application code, infrastructure configurations, and architectural designs throughout the SDLC.

**Skills:**

- Vulnerability scanning
- Static & dynamic analysis
- Threat modeling
- Penetration testing
- Compliance auditing
- Secure coding review

---

## Adding a New Agent

1. **Implement** the agent in `src/agents/my_agent.py` (use `src/agents/_template.py` as a guide).
2. **Register** it in `registry.yaml`:

    ```yaml
    agents:
      - name: my_agent
        description: What this agent does.
        endpoint: /a2a/my_agent
        skills:
          - skill one
          - skill two
        status: active
    ```

3. **Wire** it into `src/main.py` — add the module name to `AGENT_MODULES`.
4. The registry watcher **hot-reloads** `registry.yaml` automatically; a server restart is only needed for new Python code.

See the [Development Guide](development.md) for more details.
