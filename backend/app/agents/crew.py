"""
Crew Assembly — Wires all CrewAI agents into a cohesive incubation crew.
Manages agent creation, task configuration, and crew execution.
"""

import structlog
from typing import Optional
from crewai import Crew, Process

from app.services.llm import get_llm_service
from app.agents.market_analyst import create_market_analyst, create_market_research_task
from app.agents.tech_architect import create_tech_architect, create_architecture_task
from app.agents.growth_strategist import create_growth_strategist, create_gtm_strategy_task
from app.agents.financial_analyst import create_financial_analyst, create_financial_projection_task
from app.agents.legal_advisor import create_legal_advisor, create_legal_review_task

logger = structlog.get_logger()


class IncubatorCrew:
    """
    Assembles and manages the full incubator crew of AI agents.
    Agents work sequentially, with each agent's output feeding into the next.
    """

    def __init__(self):
        self._llm_service = get_llm_service()
        self._llm = self._llm_service.get_crew_llm()
        self._agents = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """Create all specialized agents."""
        self._agents = {
            "market_analyst": create_market_analyst(self._llm),
            "tech_architect": create_tech_architect(self._llm),
            "growth_strategist": create_growth_strategist(self._llm),
            "financial_analyst": create_financial_analyst(self._llm),
            "legal_advisor": create_legal_advisor(self._llm),
        }
        logger.info("Incubator crew initialized", num_agents=len(self._agents))

    def get_agent(self, role: str):
        """Get a specific agent by role name."""
        return self._agents.get(role)

    def build_full_incubation_crew(self, idea: dict) -> Crew:
        """
        Build the full incubation crew with all agents and tasks.
        Tasks are executed sequentially with output chaining.

        Flow:
        1. Market Analyst → Market Research Report
        2. Tech Architect → Technical Architecture (informed by market research)
        3. Growth Strategist → GTM Strategy (informed by market research)
        4. Financial Analyst → Financial Projections (informed by market + growth)
        5. Legal Advisor → Legal Review (informed by tech architecture)
        """
        # Create tasks with proper context chaining
        market_task = create_market_research_task(
            self._agents["market_analyst"],
            idea,
        )
        architecture_task = create_architecture_task(
            self._agents["tech_architect"],
            idea,
        )
        growth_task = create_gtm_strategy_task(
            self._agents["growth_strategist"],
            idea,
        )
        financial_task = create_financial_projection_task(
            self._agents["financial_analyst"],
            idea,
        )
        legal_task = create_legal_review_task(
            self._agents["legal_advisor"],
            idea,
        )

        # Set context dependencies — later tasks receive outputs of earlier ones
        architecture_task.context = [market_task]
        growth_task.context = [market_task]
        financial_task.context = [market_task, growth_task]
        legal_task.context = [architecture_task]

        crew = Crew(
            agents=[
                self._agents["market_analyst"],
                self._agents["tech_architect"],
                self._agents["growth_strategist"],
                self._agents["financial_analyst"],
                self._agents["legal_advisor"],
            ],
            tasks=[
                market_task,
                architecture_task,
                growth_task,
                financial_task,
                legal_task,
            ],
            process=Process.sequential,
            verbose=True,
            memory=True,
            cache=True,
            max_rpm=10,  # Rate limit to avoid API throttling
        )

        logger.info("Full incubation crew assembled", idea_title=idea.get("title"))
        return crew

    def build_research_only_crew(self, idea: dict) -> Crew:
        """Build a crew for market research only (faster execution)."""
        market_task = create_market_research_task(
            self._agents["market_analyst"],
            idea,
        )

        crew = Crew(
            agents=[self._agents["market_analyst"]],
            tasks=[market_task],
            process=Process.sequential,
            verbose=True,
        )

        logger.info("Research-only crew assembled", idea_title=idea.get("title"))
        return crew

    def build_core_crew(self, idea: dict) -> Crew:
        """Build a crew with only the core 3 agents (Market, Tech, Growth)."""
        market_task = create_market_research_task(
            self._agents["market_analyst"],
            idea,
        )
        architecture_task = create_architecture_task(
            self._agents["tech_architect"],
            idea,
        )
        growth_task = create_gtm_strategy_task(
            self._agents["growth_strategist"],
            idea,
        )

        architecture_task.context = [market_task]
        growth_task.context = [market_task]

        crew = Crew(
            agents=[
                self._agents["market_analyst"],
                self._agents["tech_architect"],
                self._agents["growth_strategist"],
            ],
            tasks=[market_task, architecture_task, growth_task],
            process=Process.sequential,
            verbose=True,
            memory=True,
            cache=True,
        )

        logger.info("Core crew assembled", idea_title=idea.get("title"))
        return crew

    async def run_full_incubation(self, idea: dict) -> dict:
        """
        Execute the full incubation process and return all reports.

        Returns:
            dict with keys: market_research, tech_architecture,
            growth_strategy, financial_projection, legal_review
        """
        crew = self.build_full_incubation_crew(idea)

        logger.info("Starting full incubation", idea_title=idea.get("title"))
        result = crew.kickoff()

        # Parse task outputs
        outputs = {}
        task_names = [
            "market_research",
            "tech_architecture",
            "growth_strategy",
            "financial_projection",
            "legal_review",
        ]

        for i, task_output in enumerate(result.tasks_output):
            if i < len(task_names):
                outputs[task_names[i]] = task_output.raw

        outputs["full_output"] = result.raw
        outputs["token_usage"] = result.token_usage if hasattr(result, "token_usage") else {}

        logger.info(
            "Full incubation completed",
            idea_title=idea.get("title"),
            num_reports=len(outputs),
        )
        return outputs

    async def run_single_agent(self, role: str, idea: dict) -> str:
        """Run a single agent's task and return the output."""
        agent = self._agents.get(role)
        if not agent:
            raise ValueError(f"Unknown agent role: {role}")

        task_creators = {
            "market_analyst": lambda: create_market_research_task(agent, idea),
            "tech_architect": lambda: create_architecture_task(agent, idea),
            "growth_strategist": lambda: create_gtm_strategy_task(agent, idea),
            "financial_analyst": lambda: create_financial_projection_task(agent, idea),
            "legal_advisor": lambda: create_legal_review_task(agent, idea),
        }

        task = task_creators[role]()
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff()
        return result.raw


_incubator_crew: Optional[IncubatorCrew] = None


def get_incubator_crew() -> IncubatorCrew:
    """Get or create the global IncubatorCrew singleton."""
    global _incubator_crew
    if _incubator_crew is None:
        _incubator_crew = IncubatorCrew()
    return _incubator_crew
