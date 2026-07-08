"""
Product Manager Agent — CrewAI
Creates detailed product specs, user stories, and wireframe descriptions.
"""

from crewai import Agent, Task
from app.tools.search import WebSearchTool

def create_product_manager(llm) -> Agent:
    return Agent(
        role="Lead Product Manager",
        goal=(
            "Define the absolute core Minimum Viable Product (MVP) that provides "
            "immediate value. Write hyper-detailed user stories, define exact feature scopes, "
            "and describe UI/UX wireframes so developers can start coding immediately."
        ),
        backstory=(
            "You are a ruthless Product Manager who ships. You cut scope aggressively. "
            "You know that a feature without a user story is just a dream. "
            "You provide highly detailed, actionable product specifications."
        ),
        tools=[WebSearchTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

def create_product_spec_task(agent: Agent, idea: dict) -> Task:
    return Task(
        description=(
            f"Create a hyper-detailed product specification for: {idea.get('title', 'N/A')}\n\n"
            f"Description: {idea.get('description', 'N/A')}\n\n"
            f"Define:\n"
            f"- MVP Scope vs V1 Scope\n"
            f"- Detailed User Stories (As a [user], I want [action] so that [benefit])\n"
            f"- UI/UX Wireframe descriptions for the 3 main screens\n"
            f"- Product metrics to track immediately post-launch\n"
        ),
        expected_output=(
            "A comprehensive product spec in markdown format."
        ),
        agent=agent,
    )
