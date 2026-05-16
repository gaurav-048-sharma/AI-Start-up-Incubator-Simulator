"""
Legal & IP Advisor Agent — CrewAI
Analyzes intellectual property landscape, regulatory concerns,
compliance requirements, and legal risks.
"""

from crewai import Agent, Task
from app.tools.search import WebSearchTool


def create_legal_advisor(llm) -> Agent:
    """
    Create the Legal/IP Advisor agent.

    This agent specializes in:
    - Intellectual property landscape analysis
    - Regulatory compliance assessment
    - Data privacy (GDPR, CCPA) requirements
    - Terms of service and licensing considerations
    - Legal risk identification
    """
    return Agent(
        role="Startup Legal & IP Strategy Advisor",
        goal=(
            "Identify legal risks, intellectual property considerations, and regulatory "
            "requirements that could impact the startup. Provide actionable legal strategy "
            "recommendations to protect the business and ensure compliance."
        ),
        backstory=(
            "You are a startup legal advisor who has counseled over 200 startups on IP strategy, "
            "regulatory compliance, and corporate structure. You previously worked at Wilson Sonsini "
            "and Cooley, the top startup law firms in Silicon Valley. You understand patents, "
            "trademarks, trade secrets, and copyright in the tech industry. You're well-versed in "
            "GDPR, CCPA, SOC2, HIPAA, and industry-specific regulations. You always provide "
            "practical, founder-friendly advice — not just legal theory. You flag critical legal "
            "risks early and suggest cost-effective solutions for early-stage startups."
        ),
        tools=[WebSearchTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )


def create_legal_review_task(
    agent: Agent,
    idea: dict,
    tech_architecture: str = "",
) -> Task:
    """Create the comprehensive legal review task."""
    context_section = ""
    if tech_architecture:
        context_section = f"\n**Technical Architecture Context:**\n{tech_architecture[:1500]}\n"

    return Task(
        description=(
            f"Conduct a comprehensive legal and IP analysis for:\n\n"
            f"**Title:** {idea.get('title', 'N/A')}\n"
            f"**Description:** {idea.get('description', 'N/A')}\n"
            f"**Industry:** {idea.get('industry', 'Not specified')}\n"
            f"{context_section}\n"
            f"Your analysis MUST cover:\n\n"
            f"1. **Intellectual Property Landscape**\n"
            f"   - Existing patents in the space\n"
            f"   - Trademark considerations for the name/brand\n"
            f"   - Trade secret protection strategy\n"
            f"   - Open source licensing implications\n"
            f"   - IP filing recommendations and timeline\n\n"
            f"2. **Regulatory Compliance**\n"
            f"   - Industry-specific regulations\n"
            f"   - Data privacy requirements (GDPR, CCPA, etc.)\n"
            f"   - Financial regulations (if applicable)\n"
            f"   - Healthcare regulations (if applicable)\n"
            f"   - Geographic regulatory variations\n\n"
            f"3. **Corporate Structure**\n"
            f"   - Recommended entity type (C-Corp, LLC, etc.)\n"
            f"   - Incorporation jurisdiction recommendation\n"
            f"   - Cap table and equity structure advice\n"
            f"   - Founder agreement essentials\n\n"
            f"4. **Risk Assessment**\n"
            f"   - Top 5 legal risks ranked by severity\n"
            f"   - Mitigation strategy for each risk\n"
            f"   - Estimated legal budget for Year 1\n"
            f"   - Insurance recommendations\n\n"
            f"5. **Compliance Roadmap**\n"
            f"   - Immediate legal actions needed (pre-launch)\n"
            f"   - Post-launch compliance requirements\n"
            f"   - Ongoing compliance monitoring needs\n"
            f"   - Key legal milestones timeline\n"
        ),
        expected_output=(
            "A comprehensive legal analysis in markdown format with all five sections. "
            "Include specific regulations by name, estimated legal costs, priority ratings "
            "for each risk, and a clear compliance roadmap with timelines."
        ),
        agent=agent,
    )
