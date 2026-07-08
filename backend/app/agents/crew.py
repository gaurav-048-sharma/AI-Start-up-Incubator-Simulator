"""
Crew Assembly — Wires all CrewAI agents into a cohesive incubation crew.
When CrewAI is mocked (not installed), falls back to direct LLM calls
with rich prompts that mirror what the agents would produce.
"""

import structlog
import sys
from typing import Optional
import asyncio
from unittest.mock import MagicMock

from app.services.llm import get_llm_service
from app.config import get_settings

logger = structlog.get_logger()


def _is_crewai_mocked() -> bool:
    """Check if crewai module is a mock (not actually installed)."""
    crewai_mod = sys.modules.get("crewai")
    if crewai_mod is None:
        return True
    if isinstance(crewai_mod, MagicMock):
        return True
    crew_cls = getattr(crewai_mod, "Crew", None)
    if crew_cls is None or isinstance(crew_cls, MagicMock):
        return True
    return False


# ── Agent Prompt Templates ──────────────────────────────────────────

AGENT_PROMPTS = {
    "market_analyst": (
        "You are an elite, brutally honest VC Market Analyst. You must produce a hyper-detailed, 3-4 page markdown report. "
        "Avoid generic buzzwords. Your report must tell the founder EXACTLY what market they are entering, with hard data, actionable insights, and no fluff.\n\n"
        "1. **Industry Reality Check** — Current state, real challenges, actual regulations.\n"
        "2. **Hyper-Specific Target Market** — Exact buyer personas with job titles, pain points, and why they would pay.\n"
        "3. **Data-Driven Market Sizing** — Realistic TAM, SAM, and SOM with cited methodologies. Break down how you calculated this.\n"
        "4. **Competitor Tear-down** — Deep dive into 3 direct and 2 indirect competitors. What do they do well? Where do they fail?\n"
        "5. **Barriers & Strategic Pivot** — Exactly what will kill this startup and the ONE specific pivot or wedge strategy to survive.\n\n"
        "Make it highly actionable. The founder should know exactly what to do next based on this data."
    ),
    "tech_architect": (
        "You are a pragmatic, veteran Principal Engineer. You must produce a hyper-detailed, 3-4 page markdown technical blueprint. "
        "Do not just list technologies; explain EXACTLY how they connect. Provide actionable steps for Day 1.\n\n"
        "1. **System Architecture Diagram & Explanation** — Detailed text representation of the architecture. Which services connect to what?\n"
        "2. **The Exact Tech Stack** — Specific frameworks, databases (with schema hints), caching, and queue choices. Justify each.\n"
        "3. **Step-by-Step Implementation Guide** — Exactly what the developers should set up on Day 1, Day 2, and Week 1.\n"
        "4. **API & Data Flow** — How data enters the system, where it's stored, how it's processed.\n"
        "5. **DevOps & Hosting** — Specific platforms (e.g. Vercel, AWS ECS), CI/CD pipeline steps, and monitoring tools.\n"
        "6. **Cloud Cost Estimates** — Brutally honest cost breakdown for Month 1 and Month 12.\n\n"
        "Make it a literal execution manual for the engineering team."
    ),
    "product_manager": (
        "You are a ruthless, execution-focused Lead Product Manager. You must produce a hyper-detailed, 3-4 page markdown product spec. "
        "Your job is to cut scope and define an MVP that can be built in weeks, not months.\n\n"
        "1. **MVP Scope vs V1 Scope** — Exactly what features are in the MVP and what is strictly cut.\n"
        "2. **Detailed User Stories** — Write at least 10 specific user stories with acceptance criteria.\n"
        "3. **UI/UX Wireframe Descriptions** — Describe the layout, buttons, and flow of the 3 most critical screens.\n"
        "4. **Core User Journey** — Step-by-step walkthrough of the user's first 5 minutes in the app.\n"
        "5. **Success Metrics** — The exact 3 KPIs to track on launch day to know if the product is working.\n\n"
        "This must be actionable enough that a developer and designer can start working from it immediately."
    ),
    "growth_strategist": (
        "You are an aggressive, data-driven Growth Hacker. You must produce a hyper-detailed, 3-4 page markdown GTM plan. "
        "No generic advice like 'use social media'. Tell the founder EXACTLY how to get their first 100 users.\n\n"
        "1. **The Exact 'Wedge' Strategy** — The specific hyper-niche market to attack first and the messaging to use.\n"
        "2. **Zero-CAC Acquisition Playbook** — 3 exact, step-by-step scrappy tactics to get organic users (e.g., specific communities, cold email templates).\n"
        "3. **Viral Mechanics & Onboarding** — How to force users to invite others naturally within the product flow.\n"
        "4. **Pricing Psychology** — Exact dollar amounts for tiers and psychological triggers to use.\n"
        "5. **The 30-Day Launch Checklist** — A literal day-by-day, week-by-week checklist for marketing execution.\n\n"
        "Your output must be a literal playbook that the founder can execute starting tomorrow morning."
    ),
    "financial_analyst": (
        "You are a cynical, rigorous Startup CFO. You must produce a hyper-detailed, 3-4 page markdown financial model. "
        "Stress-test their viability.\n\n"
        "1. **Unit Economics Tear-down** — Exact LTV, CAC, Payback Period, and Gross Margin calculations.\n"
        "2. **Hidden Cost Structure** — Specific SaaS subscriptions, API costs, legal fees, and salaries required.\n"
        "3. **Break-even & Runway Analysis** — How many users/sales needed to break even. When do they die without funding?\n"
        "4. **Funding Strategy** — Exact amount to raise, valuation target, and milestones needed to get there.\n"
        "5. **Conservative 3-Year Projections** — Detailed quarterly breakdown.\n\n"
        "CRITICAL: At the very end of your report, you MUST output a JSON block containing the month-by-month financial projection data for the first 12 months. Enclose it exactly inside ```json and ``` tags. The JSON should be an array of objects, where each object has keys: `month` (e.g. 'Month 1'), `revenue` (number), `cost` (number), `users` (number). Example:\n"
        "```json\n"
        "[\n  {\"month\": \"Month 1\", \"revenue\": 0, \"cost\": 15000, \"users\": 100}\n]\n"
        "```"
    ),
    "operations_manager": (
        "You are a battle-tested Chief Operating Officer. You must produce a hyper-detailed, 3-4 page markdown operations manual. "
        "An idea is useless without execution. Detail the exact logistics.\n\n"
        "1. **Day 1 Logistics & Tools** — Exact SaaS tools to buy (e.g., Google Workspace, Linear, Gusto) and what they cost.\n"
        "2. **30-60-90 Day Hiring Plan** — Exact roles to hire, when to hire them, expected salaries, and equity grants.\n"
        "3. **Customer Support Playbook** — Step-by-step SOP for handling the first 10 angry customers.\n"
        "4. **Compliance & Security Ops** — How to operationalize data privacy, SOC2 prep, and internal access controls.\n"
        "5. **Founder Time Allocation** — Exact breakdown of how the CEO should spend their 80-hour work week.\n\n"
        "Provide a concrete, actionable blueprint to run the company."
    ),
    "legal_advisor": (
        "You are an elite Tech Startup Attorney. You must produce a hyper-detailed, 3-4 page markdown legal strategy. "
        "Do not give generic advice. Tell them exactly what to file and what risks they face.\n\n"
        "1. **Corporate Structure & Incorporation** — Exact entity type, jurisdiction (e.g. Delaware C-Corp), and steps to file.\n"
        "2. **IP Strategy** — Specific components to patent vs trademark vs trade secret.\n"
        "3. **Data Privacy & Terms** — Specific clauses needed in their Terms of Service and Privacy Policy based on their product.\n"
        "4. **Employment & Equity** — Exact vesting schedules (e.g., 4-year with 1-year cliff) and contractor agreements needed.\n"
        "5. **Fundraising Legal** — Step-by-step guide to issuing SAFEs, cap table management, and SEC exemptions (e.g. Rule 506b).\n\n"
        "Make it an actionable checklist so they can hand it to Clerky/Stripe Atlas or their lawyer."
    ),
}


def _format_idea_for_prompt(idea: dict) -> str:
    """Format a startup idea dict into a prompt-friendly string."""
    return (
        f"## Startup Idea\n"
        f"**Title:** {idea.get('title', 'N/A')}\n"
        f"**Description:** {idea.get('description', 'N/A')}\n"
        f"**Industry:** {idea.get('industry', 'N/A')}\n"
        f"**Target Market:** {idea.get('target_market', 'N/A')}\n"
        f"**Problem Statement:** {idea.get('problem_statement', 'N/A')}\n"
        f"**Proposed Solution:** {idea.get('proposed_solution', 'N/A')}\n"
    )


class IncubatorCrew:
    """
    Assembles and manages the full incubator crew of AI agents.
    Falls back to direct LLM calls when CrewAI is not installed.
    """

    def __init__(self):
        self._llm_service = get_llm_service()
        self._use_crewai = not _is_crewai_mocked()

        if self._use_crewai:
            try:
                from crewai import Crew, Process
                from app.agents.market_analyst import create_market_analyst, create_market_research_task
                from app.agents.tech_architect import create_tech_architect, create_architecture_task
                from app.agents.growth_strategist import create_growth_strategist, create_gtm_strategy_task
                from app.agents.financial_analyst import create_financial_analyst, create_financial_projection_task
                from app.agents.legal_advisor import create_legal_advisor, create_legal_review_task
                from app.agents.product_manager import create_product_manager, create_product_spec_task
                from app.agents.operations_manager import create_operations_manager, create_operations_plan_task

                llm = self._llm_service.get_crew_llm()
                self._agents = {
                    "market_analyst": create_market_analyst(llm),
                    "tech_architect": create_tech_architect(llm),
                    "product_manager": create_product_manager(llm),
                    "growth_strategist": create_growth_strategist(llm),
                    "financial_analyst": create_financial_analyst(llm),
                    "operations_manager": create_operations_manager(llm),
                    "legal_advisor": create_legal_advisor(llm),
                }
                logger.info("CrewAI agents initialized", num_agents=len(self._agents))
            except Exception as e:
                logger.warning("CrewAI initialization failed, using LLM-direct mode", error=str(e))
                self._use_crewai = False
                self._agents = {}
        else:
            self._agents = {}
            logger.info("CrewAI not available — using LLM-direct mode for agents")

    async def run_single_agent(self, role: str, idea: dict) -> str:
        """
        Run a single agent's task and return the output.
        Uses direct LLM calls when CrewAI is not available.
        """
        if self._use_crewai and role in self._agents:
            return await self._run_crewai_agent(role, idea)
        return await self._run_llm_direct(role, idea)

    async def _run_llm_direct(self, role: str, idea: dict) -> str:
        """Generate a report using direct LLM calls (no CrewAI)."""
        system_prompt = AGENT_PROMPTS.get(role, f"You are a {role}. Analyze the startup idea below.")
        idea_text = _format_idea_for_prompt(idea)

        logger.info("Running agent via LLM-direct", role=role, idea_title=idea.get("title"))

        try:
            result = await self._llm_service.generate(
                prompt=idea_text,
                system_prompt=system_prompt,
                provider="auto",
            )
            logger.info("Agent completed via LLM-direct",
                         role=role, output_length=len(result))
            return result
        except Exception as e:
            logger.error("LLM-direct agent failed", role=role, error=str(e))
            # Return a meaningful error report rather than crashing
            return (
                f"# {role.replace('_', ' ').title()} Report\n\n"
                f"**Note:** Report generation encountered an error: {str(e)}\n\n"
                f"## Startup: {idea.get('title', 'N/A')}\n"
                f"Report could not be fully generated. Please retry the workflow."
            )

    async def _run_crewai_agent(self, role: str, idea: dict) -> str:
        """Run an agent using CrewAI (when available)."""
        from crewai import Crew, Process
        from app.agents.market_analyst import create_market_research_task
        from app.agents.tech_architect import create_architecture_task
        from app.agents.growth_strategist import create_gtm_strategy_task
        from app.agents.financial_analyst import create_financial_projection_task
        from app.agents.legal_advisor import create_legal_review_task
        from app.agents.product_manager import create_product_spec_task
        from app.agents.operations_manager import create_operations_plan_task

        agent = self._agents.get(role)
        if not agent:
            raise ValueError(f"Unknown agent role: {role}")

        task_creators = {
            "market_analyst": lambda: create_market_research_task(agent, idea),
            "tech_architect": lambda: create_architecture_task(agent, idea),
            "product_manager": lambda: create_product_spec_task(agent, idea),
            "growth_strategist": lambda: create_gtm_strategy_task(agent, idea),
            "financial_analyst": lambda: create_financial_projection_task(agent, idea),
            "operations_manager": lambda: create_operations_plan_task(agent, idea),
            "legal_advisor": lambda: create_legal_review_task(agent, idea),
        }

        task = task_creators[role]()
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        result = await asyncio.to_thread(crew.kickoff)
        return result.raw

    async def run_full_incubation(self, idea: dict) -> dict:
        """Execute the full incubation process and return all reports."""
        roles = ["market_analyst", "tech_architect", "product_manager", "growth_strategist",
                 "financial_analyst", "operations_manager", "legal_advisor"]
        task_names = ["market_research", "tech_architecture", "product_spec", "growth_strategy",
                      "financial_projection", "operations_plan", "legal_review"]

        outputs = {}
        for role, name in zip(roles, task_names):
            outputs[name] = await self.run_single_agent(role, idea)

        logger.info("Full incubation completed", idea_title=idea.get("title"),
                     num_reports=len(outputs))
        return outputs


_incubator_crew: Optional[IncubatorCrew] = None


def get_incubator_crew() -> IncubatorCrew:
    """Get or create the global IncubatorCrew singleton."""
    global _incubator_crew
    if _incubator_crew is None:
        _incubator_crew = IncubatorCrew()
    return _incubator_crew
