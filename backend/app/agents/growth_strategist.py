"""
Growth Strategist Agent — CrewAI
Designs go-to-market strategies, user acquisition plans,
pricing models, and growth frameworks.
"""

from crewai import Agent, Task
from app.tools.search import WebSearchTool, TrendSearchTool


def create_growth_strategist(llm) -> Agent:
    """
    Create the Growth Strategist agent.

    This agent specializes in:
    - Go-to-market strategy design
    - User acquisition and retention strategies
    - Pricing model optimization
    - Growth loop identification
    - Marketing channel analysis
    - Viral/PLG mechanics
    """
    return Agent(
        role="VP of Growth Strategy",
        goal=(
            "Design data-driven growth strategies that enable startups to acquire, retain, "
            "and monetize users efficiently. Create actionable go-to-market plans with "
            "specific channels, tactics, budgets, and KPI targets."
        ),
        backstory=(
            "You are a growth leader who has driven user acquisition at companies like Notion, "
            "Figma, and Linear. You understand both product-led growth (PLG) and sales-led motions. "
            "You've managed growth budgets from $10K/month to $10M/month and know exactly which "
            "channels work at each stage. You think in terms of growth loops, not funnels — "
            "every user should help bring the next user. You're obsessed with unit economics: "
            "CAC, LTV, payback period, and net dollar retention. You balance short-term tactics "
            "(paid ads, outbound) with long-term moats (content, community, SEO, network effects)."
        ),
        tools=[
            WebSearchTool(),
            TrendSearchTool(),
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )


def create_gtm_strategy_task(agent: Agent, idea: dict, market_research: str = "") -> Task:
    """Create the go-to-market strategy task."""
    context_section = ""
    if market_research:
        context_section = f"\n**Market Research Context:**\n{market_research[:2000]}\n"

    return Task(
        description=(
            f"Design a comprehensive go-to-market (GTM) and growth strategy for:\n\n"
            f"**Title:** {idea.get('title', 'N/A')}\n"
            f"**Description:** {idea.get('description', 'N/A')}\n"
            f"**Target Market:** {idea.get('target_market', 'Not specified')}\n"
            f"**Proposed Solution:** {idea.get('proposed_solution', 'Not specified')}\n"
            f"{context_section}\n"
            f"Your strategy MUST include:\n\n"
            f"1. **Go-to-Market Strategy**\n"
            f"   - Launch strategy (PLG, sales-led, or hybrid)\n"
            f"   - Target early adopter profile (ICP)\n"
            f"   - Value proposition and messaging framework\n"
            f"   - Launch timeline and milestones\n"
            f"   - First 100 customers playbook\n\n"
            f"2. **User Acquisition Channels**\n"
            f"   - Ranked list of acquisition channels by expected ROI\n"
            f"   - For each channel: strategy, estimated CAC, timeline to results\n"
            f"   - Channels to consider: SEO/Content, Paid Search, Social Ads,\n"
            f"     Community, Partnerships, PR, Product Hunt, outbound, referrals\n\n"
            f"3. **Pricing Strategy**\n"
            f"   - Pricing model (freemium, trial, usage-based, per-seat)\n"
            f"   - Tier structure with specific price points\n"
            f"   - Competitive pricing analysis\n"
            f"   - Price sensitivity assessment\n"
            f"   - Monetization timeline\n\n"
            f"4. **Growth Loops & Retention**\n"
            f"   - Primary growth loop description\n"
            f"   - Viral coefficient estimation\n"
            f"   - Retention strategy (onboarding, engagement, reactivation)\n"
            f"   - Network effects potential\n"
            f"   - Key activation metrics\n\n"
            f"5. **KPIs & Metrics Framework**\n"
            f"   - North Star Metric\n"
            f"   - Input metrics that drive the North Star\n"
            f"   - Target metrics for Month 1, 3, 6, 12\n"
            f"   - Monitoring and reporting cadence\n\n"
            f"6. **Budget Allocation**\n"
            f"   - Monthly marketing budget recommendation\n"
            f"   - Budget split across channels\n"
            f"   - Expected ROI per channel\n"
            f"   - Break-even timeline\n"
        ),
        expected_output=(
            "A comprehensive growth strategy document in markdown format with all six sections. "
            "Include specific dollar amounts for budgets, target metrics with numbers, "
            "channel-by-channel CAC estimates, and a month-by-month execution timeline."
        ),
        agent=agent,
    )


def create_pricing_optimization_task(agent: Agent, idea: dict) -> Task:
    """Create a focused pricing strategy task."""
    return Task(
        description=(
            f"Design an optimal pricing strategy for: {idea.get('title', 'N/A')}\n"
            f"Description: {idea.get('description', 'N/A')}\n\n"
            f"Analyze:\n"
            f"- Competitor pricing benchmarks\n"
            f"- Value metric identification\n"
            f"- Freemium vs. trial vs. paid-only\n"
            f"- Tier structure (3-4 tiers recommended)\n"
            f"- Enterprise pricing approach\n"
            f"- Discount strategy\n"
            f"- Annual vs. monthly billing impact\n"
        ),
        expected_output=(
            "A pricing strategy with specific tier names, features per tier, "
            "exact price points, and projected revenue impact."
        ),
        agent=agent,
    )
