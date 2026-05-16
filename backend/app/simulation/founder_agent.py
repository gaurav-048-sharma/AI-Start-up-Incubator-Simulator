"""
Founder Agent — AutoGen
Represents the startup founder during investor pitch simulations.
"""

import structlog
from app.config import get_settings

logger = structlog.get_logger()

FOUNDER_SYSTEM_PROMPT = """You are a passionate, articulate startup founder pitching your company to investors.

Your startup:
{idea_summary}

Key metrics and highlights:
{financial_highlights}

Your style:
- Confident but not arrogant
- Data-driven — cite specific numbers from your research
- Honest about risks and how you'll mitigate them
- Passionate about the problem you're solving
- Concise — investors' time is valuable
- Address questions directly, don't dodge
- Tell compelling stories about user pain points
- Show traction or a clear path to traction

Always maintain the persona of a real founder. If asked about something you don't
know, say you'll follow up rather than making something up.
"""


def build_founder_system_prompt(idea: dict, executive_summary: str = "", financial: str = "") -> str:
    """Build the founder agent's system prompt with context."""
    idea_summary = (
        f"Name: {idea.get('title', 'Our Startup')}\n"
        f"Description: {idea.get('description', 'N/A')}\n"
        f"Industry: {idea.get('industry', 'Technology')}\n"
        f"Problem: {idea.get('problem_statement', 'N/A')}\n"
        f"Solution: {idea.get('proposed_solution', 'N/A')}\n"
    )

    if executive_summary:
        idea_summary += f"\nExecutive Summary:\n{executive_summary[:2000]}"

    financial_highlights = financial[:1500] if financial else "Financial projections will be shared during the pitch."

    return FOUNDER_SYSTEM_PROMPT.format(
        idea_summary=idea_summary,
        financial_highlights=financial_highlights,
    )
