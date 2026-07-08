"""
Operations Manager Agent — CrewAI
Creates day 1 logistics, hiring plan, and standard operating procedures.
"""

from crewai import Agent, Task
from app.tools.search import WebSearchTool

def create_operations_manager(llm) -> Agent:
    return Agent(
        role="Chief Operating Officer",
        goal=(
            "Define the exact Day 1 operational logistics, hiring plan, and supply chain/vendor "
            "setup required to run the company efficiently without wasting money."
        ),
        backstory=(
            "You are a battle-tested COO. You know that an idea is useless if the execution "
            "fails. You focus on people, processes, and tools. You provide exact lists of "
            "SaaS tools to buy, roles to hire, and processes to set up."
        ),
        tools=[WebSearchTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

def create_operations_plan_task(agent: Agent, idea: dict) -> Task:
    return Task(
        description=(
            f"Create a hyper-detailed operations plan for: {idea.get('title', 'N/A')}\n\n"
            f"Description: {idea.get('description', 'N/A')}\n\n"
            f"Define:\n"
            f"- 30-60-90 Day Hiring Plan (with expected salaries)\n"
            f"- Internal SaaS Stack (CRM, HR, Support tools with costs)\n"
            f"- Standard Operating Procedures (SOPs) for customer support\n"
            f"- Legal/Compliance operational integration (e.g. data privacy checklist)\n"
        ),
        expected_output=(
            "A comprehensive operations plan in markdown format."
        ),
        agent=agent,
    )
