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
        "You are a Senior Market Research Analyst specializing in startup market analysis. "
        "Produce a comprehensive market research report for the following startup idea.\n\n"
        "Include these sections with DETAILED analysis (not placeholders):\n"
        "1. **Industry Overview** — Current state, trends, growth rate, key players\n"
        "2. **Target Market Analysis** — Demographics, psychographics, buyer personas\n"
        "3. **Market Size** — TAM, SAM, SOM with justification and sources\n"
        "4. **Competitive Landscape** — Direct/indirect competitors, SWOT analysis\n"
        "5. **Market Trends & Opportunities** — Emerging trends, unmet needs\n"
        "6. **Barriers to Entry** — Regulatory, technical, financial barriers\n"
        "7. **Key Recommendations** — Strategic insights for market entry\n\n"
        "Format using markdown headers and bullet points. Be specific with numbers and data."
    ),
    "tech_architect": (
        "You are a Senior Technical Architect with expertise in scalable systems. "
        "Design a complete technical architecture for the following startup idea.\n\n"
        "Include these sections with DETAILED specifications:\n"
        "1. **System Architecture Overview** — High-level architecture diagram description\n"
        "2. **Technology Stack** — Frontend, backend, database, infrastructure with justifications\n"
        "3. **Core Components** — Microservices/modules breakdown, responsibilities\n"
        "4. **Data Architecture** — Database design, data flow, storage strategy\n"
        "5. **AI/ML Integration** — If applicable, model architecture, training pipeline\n"
        "6. **Security Architecture** — Auth, encryption, compliance requirements\n"
        "7. **Scalability Plan** — Auto-scaling, load balancing, performance targets\n"
        "8. **DevOps & Deployment** — CI/CD pipeline, monitoring, infrastructure-as-code\n"
        "9. **Cost Estimates** — Cloud infrastructure monthly costs at different scales\n\n"
        "Format using markdown. Be specific with technology choices and rationale."
    ),
    "growth_strategist": (
        "You are a Growth Strategy Consultant who has helped 50+ startups scale. "
        "Create a comprehensive go-to-market and growth strategy for the following startup.\n\n"
        "Include these sections:\n"
        "1. **Go-to-Market Strategy** — Launch plan, phased rollout, beta strategy\n"
        "2. **Customer Acquisition Channels** — Ranked by expected ROI\n"
        "3. **Pricing Strategy** — Tier structure, competitive positioning\n"
        "4. **Growth Loops & Viral Mechanics** — Referral programs, network effects\n"
        "5. **Content & SEO Strategy** — Content pillars, keyword strategy\n"
        "6. **Partnership Strategy** — Potential partners, integration opportunities\n"
        "7. **Key Metrics & KPIs** — CAC, LTV, churn rate targets\n"
        "8. **90-Day Launch Plan** — Week-by-week action items\n\n"
        "Format using markdown. Include specific numbers and benchmarks."
    ),
    "financial_analyst": (
        "You are a Senior Financial Analyst specializing in startup financial modeling. "
        "Create detailed financial projections for the following startup.\n\n"
        "Include these sections:\n"
        "1. **Revenue Model** — Pricing tiers, revenue streams, unit economics\n"
        "2. **3-Year Financial Projections** — Monthly Year 1, quarterly Years 2-3\n"
        "3. **Cost Structure** — Fixed costs, variable costs, COGS breakdown\n"
        "4. **Key Metrics** — MRR, ARR, CAC, LTV, LTV/CAC ratio, payback period\n"
        "5. **Break-even Analysis** — When and at what user count\n"
        "6. **Funding Requirements** — How much to raise, use of funds, runway\n"
        "7. **Valuation Analysis** — Comparable valuations, revenue multiples\n"
        "8. **Risk Factors** — Financial risks and mitigation strategies\n\n"
        "Format using markdown with tables for projections. Use realistic numbers."
    ),
    "legal_advisor": (
        "You are a Startup Legal Advisor with expertise in tech startups. "
        "Provide a comprehensive legal and IP review for the following startup.\n\n"
        "Include these sections:\n"
        "1. **Corporate Structure** — Recommended entity type, jurisdiction, rationale\n"
        "2. **Intellectual Property** — Patent strategy, trademark filing, trade secrets\n"
        "3. **Data Privacy & Compliance** — GDPR, CCPA, industry-specific regulations\n"
        "4. **Licensing & Open Source** — Software license audit, compliance requirements\n"
        "5. **Employment & Contractor Law** — Key considerations for early hiring\n"
        "6. **Terms of Service & Privacy Policy** — Key provisions needed\n"
        "7. **Fundraising Legal** — SAFE/convertible note considerations, SEC compliance\n"
        "8. **Risk Assessment** — Top legal risks and mitigation steps\n\n"
        "Format using markdown. Be specific about actions needed."
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

                llm = self._llm_service.get_crew_llm()
                self._agents = {
                    "market_analyst": create_market_analyst(llm),
                    "tech_architect": create_tech_architect(llm),
                    "growth_strategist": create_growth_strategist(llm),
                    "financial_analyst": create_financial_analyst(llm),
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

        result = await asyncio.to_thread(crew.kickoff)
        return result.raw

    async def run_full_incubation(self, idea: dict) -> dict:
        """Execute the full incubation process and return all reports."""
        roles = ["market_analyst", "tech_architect", "growth_strategist",
                 "financial_analyst", "legal_advisor"]
        task_names = ["market_research", "tech_architecture", "growth_strategy",
                      "financial_projection", "legal_review"]

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
