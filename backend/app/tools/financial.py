"""
Financial modeling tools for revenue projections, unit economics,
and startup financial analysis.
"""

import structlog
from crewai.tools import BaseTool

logger = structlog.get_logger()


class FinancialModelTool(BaseTool):
    """
    Creates financial models including revenue projections,
    unit economics, burn rate calculations, and funding requirements.
    """

    name: str = "financial_model"
    description: str = (
        "Create financial models and projections for startups. "
        "Generates revenue forecasts, unit economics analysis, "
        "burn rate calculations, runway estimates, and funding requirements. "
        "Input should describe the business model, pricing, and target metrics."
    )

    def _run(self, query: str) -> str:
        """Generate a financial model framework."""
        logger.info("Financial model requested", query=query[:100])

        return (
            f"**Financial Model Generation for:** {query}\n\n"
            f"Create a comprehensive financial model covering:\n\n"
            f"## Revenue Projections (3-Year)\n"
            f"- Year 1: Conservative / Base / Optimistic scenarios\n"
            f"- Year 2: Growth trajectory with key assumptions\n"
            f"- Year 3: Scale projections\n\n"
            f"## Unit Economics\n"
            f"- Customer Acquisition Cost (CAC)\n"
            f"- Lifetime Value (LTV)\n"
            f"- LTV:CAC Ratio\n"
            f"- Payback Period\n"
            f"- Gross Margin\n\n"
            f"## Burn Rate & Runway\n"
            f"- Monthly Operating Expenses breakdown\n"
            f"- Monthly Burn Rate\n"
            f"- Runway at current burn\n\n"
            f"## Funding Requirements\n"
            f"- Pre-seed / Seed requirements\n"
            f"- Series A criteria and timeline\n"
            f"- Use of funds allocation\n\n"
            f"## Key Assumptions\n"
            f"- Market size assumptions\n"
            f"- Growth rate assumptions\n"
            f"- Pricing assumptions\n"
            f"- Churn rate assumptions\n"
        )


class ValuationTool(BaseTool):
    """Calculates startup valuation using multiple methodologies."""

    name: str = "valuation_calculator"
    description: str = (
        "Calculate startup valuation using multiple methodologies: "
        "comparable analysis, DCF, revenue multiples, and Berkus method. "
        "Input should include revenue, growth rate, market size, and stage."
    )

    def _run(self, query: str) -> str:
        """Generate valuation analysis."""
        logger.info("Valuation calculation requested", query=query[:100])

        return (
            f"**Valuation Analysis for:** {query}\n\n"
            f"Calculate valuation using:\n"
            f"1. **Comparable Company Analysis** — Based on similar startups\n"
            f"2. **Revenue Multiples** — Industry-standard revenue multiples\n"
            f"3. **DCF Analysis** — Discounted cash flow projections\n"
            f"4. **Berkus Method** — For pre-revenue startups\n"
            f"5. **Scorecard Method** — Weighted factor comparison\n\n"
            f"Provide a valuation range with confidence levels.\n"
        )


class MarketSizingTool(BaseTool):
    """Calculates TAM, SAM, and SOM for market sizing."""

    name: str = "market_sizing"
    description: str = (
        "Calculate Total Addressable Market (TAM), Serviceable Addressable Market (SAM), "
        "and Serviceable Obtainable Market (SOM) for a startup idea. "
        "Uses both top-down and bottom-up approaches."
    )

    def _run(self, query: str) -> str:
        """Generate market sizing analysis."""
        logger.info("Market sizing requested", query=query[:100])

        return (
            f"**Market Sizing Analysis for:** {query}\n\n"
            f"## Top-Down Approach\n"
            f"- Total Addressable Market (TAM): Total global market value\n"
            f"- Serviceable Addressable Market (SAM): Segment you can serve\n"
            f"- Serviceable Obtainable Market (SOM): Realistic capture in 3-5 years\n\n"
            f"## Bottom-Up Approach\n"
            f"- Number of potential customers × Average revenue per customer\n"
            f"- Customer segment breakdown\n"
            f"- Geographic expansion plan\n\n"
            f"## Growth Projections\n"
            f"- CAGR for the market\n"
            f"- Key growth drivers\n"
            f"- Market maturity assessment\n"
        )
