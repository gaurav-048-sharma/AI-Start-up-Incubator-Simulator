"""
Market Analyst Agent — CrewAI
Conducts comprehensive market research including TAM/SAM/SOM analysis,
competitor mapping, trend identification, and market validation.
"""

from crewai import Agent, Task
from app.tools.search import WebSearchTool, CompetitorSearchTool, TrendSearchTool
from app.tools.financial import MarketSizingTool


def create_market_analyst(llm) -> Agent:
    """
    Create the Market Analyst agent with research tools.

    This agent specializes in:
    - Market sizing (TAM/SAM/SOM)
    - Competitor analysis and mapping
    - Industry trend identification
    - Customer segment analysis
    - Market validation and opportunity scoring
    """
    return Agent(
        role="Senior Market Research Analyst",
        goal=(
            "Conduct thorough, data-driven market research to validate startup ideas. "
            "Identify market opportunities, size the addressable market, map competitors, "
            "and assess the viability of the startup concept in the current market landscape."
        ),
        backstory=(
            "You are a veteran market research analyst with 15+ years of experience at "
            "top consulting firms (McKinsey, BCG, Bain). You've analyzed hundreds of markets "
            "across technology, fintech, healthtech, and enterprise SaaS. You're known for "
            "your rigorous, data-backed analysis and your ability to identify hidden market "
            "opportunities that others miss. You always quantify your findings with real "
            "numbers and cite credible sources. You think in frameworks: Porter's Five Forces, "
            "SWOT, PESTLE, and Blue Ocean Strategy."
        ),
        tools=[
            WebSearchTool(),
            CompetitorSearchTool(),
            TrendSearchTool(),
            MarketSizingTool(),
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )


def create_market_research_task(agent: Agent, idea: dict) -> Task:
    """Create the comprehensive market research task."""
    return Task(
        description=(
            f"Conduct a comprehensive market research analysis for the following startup idea:\n\n"
            f"**Title:** {idea.get('title', 'N/A')}\n"
            f"**Description:** {idea.get('description', 'N/A')}\n"
            f"**Industry:** {idea.get('industry', 'Not specified')}\n"
            f"**Target Market:** {idea.get('target_market', 'Not specified')}\n"
            f"**Problem Statement:** {idea.get('problem_statement', 'Not specified')}\n"
            f"**Proposed Solution:** {idea.get('proposed_solution', 'Not specified')}\n\n"
            f"Your analysis MUST cover:\n\n"
            f"1. **Market Sizing (TAM/SAM/SOM)**\n"
            f"   - Total Addressable Market with dollar values\n"
            f"   - Serviceable Addressable Market segmentation\n"
            f"   - Serviceable Obtainable Market (realistic 3-year capture)\n"
            f"   - Growth rates and CAGR projections\n\n"
            f"2. **Competitive Landscape**\n"
            f"   - Direct competitors (list top 5-10)\n"
            f"   - Indirect competitors and substitutes\n"
            f"   - Competitive advantages and moats\n"
            f"   - Market positioning map\n"
            f"   - Competitor funding and valuation data\n\n"
            f"3. **Industry Trends**\n"
            f"   - Current macro and micro trends\n"
            f"   - Emerging technologies impacting the space\n"
            f"   - Regulatory landscape changes\n"
            f"   - Consumer behavior shifts\n\n"
            f"4. **Customer Analysis**\n"
            f"   - Primary customer segments\n"
            f"   - Customer pain points and needs\n"
            f"   - Willingness to pay assessment\n"
            f"   - Customer acquisition channels\n\n"
            f"5. **Opportunity Score**\n"
            f"   - Rate the market opportunity from 1-10\n"
            f"   - Key risks and mitigation strategies\n"
            f"   - Timing assessment (why now?)\n"
            f"   - Verdict: GO / CONDITIONAL / NO-GO\n"
        ),
        expected_output=(
            "A structured market research report in markdown format with all five sections "
            "completed with specific data points, dollar amounts, competitor names, and a "
            "clear opportunity score with justification. Include sources where possible."
        ),
        agent=agent,
    )


def create_competitor_deep_dive_task(agent: Agent, idea: dict) -> Task:
    """Create a focused competitor analysis task."""
    return Task(
        description=(
            f"Perform a deep-dive competitive analysis for: {idea.get('title', 'N/A')}\n"
            f"Industry: {idea.get('industry', 'N/A')}\n\n"
            f"For each competitor found, analyze:\n"
            f"- Company name and founding year\n"
            f"- Product/service description\n"
            f"- Pricing model and tiers\n"
            f"- Known funding (rounds, amounts, investors)\n"
            f"- Estimated ARR or revenue\n"
            f"- Key differentiators\n"
            f"- Strengths and weaknesses\n"
            f"- Market share estimate\n\n"
            f"Create a competitive positioning matrix showing where the startup "
            f"could differentiate."
        ),
        expected_output=(
            "A detailed competitor analysis table with at least 5 competitors, "
            "a SWOT matrix, and a clear differentiation strategy recommendation."
        ),
        agent=agent,
    )
