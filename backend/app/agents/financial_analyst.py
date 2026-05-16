"""
Financial Analyst Agent — CrewAI
Creates financial projections, unit economics models,
burn rate calculations, and funding strategy recommendations.
"""

from crewai import Agent, Task
from app.tools.financial import FinancialModelTool, ValuationTool, MarketSizingTool
from app.tools.search import WebSearchTool


def create_financial_analyst(llm) -> Agent:
    """
    Create the Financial Analyst agent.

    This agent specializes in:
    - Revenue and expense projections
    - Unit economics modeling
    - Burn rate and runway calculations
    - Funding strategy and valuation
    - Financial risk assessment
    """
    return Agent(
        role="Startup Financial Analyst & CFO Advisor",
        goal=(
            "Build comprehensive financial models for startups that accurately project "
            "revenue, costs, and funding needs. Create investor-ready financial projections "
            "with clear assumptions and scenario analysis."
        ),
        backstory=(
            "You are a financial analyst with deep startup expertise, having worked at "
            "Sequoia Capital and a16z evaluating hundreds of startup financials. You've "
            "helped 50+ startups build their financial models, from pre-seed pitch decks "
            "to Series C growth projections. You understand SaaS metrics (ARR, MRR, NRR, "
            "churn, expansion revenue), marketplace economics (GMV, take rate), and "
            "consumer metrics (DAU/MAU, ARPU). You always stress-test assumptions and "
            "present multiple scenarios. Your models are known for being realistic rather "
            "than optimistic — investors trust your numbers."
        ),
        tools=[
            FinancialModelTool(),
            ValuationTool(),
            MarketSizingTool(),
            WebSearchTool(),
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )


def create_financial_projection_task(
    agent: Agent,
    idea: dict,
    market_research: str = "",
    growth_strategy: str = "",
) -> Task:
    """Create the comprehensive financial projection task."""
    context_parts = []
    if market_research:
        context_parts.append(f"**Market Research:**\n{market_research[:1500]}")
    if growth_strategy:
        context_parts.append(f"**Growth Strategy:**\n{growth_strategy[:1500]}")
    context_section = "\n\n".join(context_parts)

    return Task(
        description=(
            f"Create comprehensive financial projections for:\n\n"
            f"**Title:** {idea.get('title', 'N/A')}\n"
            f"**Description:** {idea.get('description', 'N/A')}\n"
            f"**Industry:** {idea.get('industry', 'Not specified')}\n\n"
            f"{context_section}\n\n"
            f"Your financial model MUST include:\n\n"
            f"1. **Revenue Projections (3-Year)**\n"
            f"   - Monthly recurring revenue (MRR) build-up\n"
            f"   - Three scenarios: Conservative, Base, Optimistic\n"
            f"   - Revenue by product line / tier\n"
            f"   - Key revenue assumptions and drivers\n"
            f"   - Annual recurring revenue (ARR) targets\n\n"
            f"2. **Unit Economics**\n"
            f"   - Customer Acquisition Cost (CAC) by channel\n"
            f"   - Lifetime Value (LTV) calculation with assumptions\n"
            f"   - LTV:CAC ratio and target\n"
            f"   - Payback period in months\n"
            f"   - Gross margin breakdown\n"
            f"   - Contribution margin analysis\n\n"
            f"3. **Operating Expenses (3-Year)**\n"
            f"   - Headcount plan and salary costs\n"
            f"   - Infrastructure / hosting costs\n"
            f"   - Marketing and sales expenses\n"
            f"   - General & administrative costs\n"
            f"   - R&D investment\n\n"
            f"4. **Burn Rate & Runway**\n"
            f"   - Monthly burn rate by quarter\n"
            f"   - Cash runway at current burn\n"
            f"   - Break-even timeline\n"
            f"   - Cash flow projections\n\n"
            f"5. **Funding Strategy**\n"
            f"   - Recommended funding rounds and amounts\n"
            f"   - Pre-money valuation justification\n"
            f"   - Use of funds breakdown (percentage allocation)\n"
            f"   - Key milestones for each funding stage\n"
            f"   - Dilution impact analysis\n\n"
            f"6. **Financial Risks & Sensitivities**\n"
            f"   - Key assumption sensitivity analysis\n"
            f"   - Worst-case scenario planning\n"
            f"   - Capital efficiency benchmarks vs. industry\n"
        ),
        expected_output=(
            "A comprehensive financial model document in markdown with tables showing "
            "monthly/quarterly projections for Year 1 and annual for Years 2-3. Include "
            "specific dollar amounts, percentages, headcount numbers, and clear assumptions. "
            "Format financial data in markdown tables."
        ),
        agent=agent,
    )
