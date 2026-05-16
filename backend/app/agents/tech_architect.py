"""
Tech Architect Agent — CrewAI
Designs technical architecture, recommends tech stacks,
assesses feasibility, and estimates development timelines.
"""

from crewai import Agent, Task
from app.tools.code_executor import CodeAnalysisTool, TechStackEvaluator
from app.tools.search import WebSearchTool


def create_tech_architect(llm) -> Agent:
    """
    Create the Tech Architect agent with analysis tools.

    This agent specializes in:
    - Technology stack selection and justification
    - System architecture design
    - Scalability and performance planning
    - Infrastructure cost estimation
    - Development timeline and team sizing
    - Technical risk assessment
    """
    return Agent(
        role="Chief Technology Architect",
        goal=(
            "Design robust, scalable, and cost-effective technical architectures for startups. "
            "Select the optimal technology stack based on the product requirements, team constraints, "
            "budget, and time-to-market goals. Provide actionable technical blueprints."
        ),
        backstory=(
            "You are a CTO-level architect who has built and scaled products at companies like "
            "Stripe, Vercel, and multiple YC startups. You've designed systems handling millions "
            "of users and billions of transactions. You favor pragmatic choices — using boring "
            "technology where it works, and cutting-edge tech only when it provides a clear advantage. "
            "You think deeply about developer experience, operational complexity, and total cost of "
            "ownership. You always consider the startup's stage: an MVP doesn't need Kubernetes, "
            "but a Series B product needs proper observability. You provide architecture diagrams, "
            "tech stack comparisons, and realistic timelines."
        ),
        tools=[
            CodeAnalysisTool(),
            TechStackEvaluator(),
            WebSearchTool(),
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )


def create_architecture_task(agent: Agent, idea: dict, market_research: str = "") -> Task:
    """Create the technical architecture design task."""
    context_section = ""
    if market_research:
        context_section = f"\n**Market Research Context:**\n{market_research[:2000]}\n"

    return Task(
        description=(
            f"Design the complete technical architecture for the following startup:\n\n"
            f"**Title:** {idea.get('title', 'N/A')}\n"
            f"**Description:** {idea.get('description', 'N/A')}\n"
            f"**Proposed Solution:** {idea.get('proposed_solution', 'Not specified')}\n"
            f"{context_section}\n"
            f"Your architecture design MUST include:\n\n"
            f"1. **Technology Stack Recommendation**\n"
            f"   - Frontend framework and libraries\n"
            f"   - Backend language and framework\n"
            f"   - Database(s) selection with justification\n"
            f"   - Caching strategy\n"
            f"   - Message queues / event systems\n"
            f"   - Cloud provider and services\n"
            f"   - DevOps and CI/CD tools\n"
            f"   - Monitoring and observability\n\n"
            f"2. **System Architecture**\n"
            f"   - High-level architecture diagram (described in text)\n"
            f"   - API design approach (REST, GraphQL, gRPC)\n"
            f"   - Authentication and authorization strategy\n"
            f"   - Data flow and processing pipelines\n"
            f"   - Third-party integrations needed\n\n"
            f"3. **Scalability Plan**\n"
            f"   - MVP architecture (0-1K users)\n"
            f"   - Growth architecture (1K-100K users)\n"
            f"   - Scale architecture (100K+ users)\n"
            f"   - Bottleneck identification and mitigation\n\n"
            f"4. **Development Roadmap**\n"
            f"   - MVP scope and timeline (target: 8-12 weeks)\n"
            f"   - V1.0 features and timeline\n"
            f"   - Team composition and roles needed\n"
            f"   - Key technical milestones\n\n"
            f"5. **Infrastructure Costs**\n"
            f"   - Monthly cost estimate for MVP\n"
            f"   - Monthly cost at 10K users\n"
            f"   - Monthly cost at 100K users\n"
            f"   - Cost optimization strategies\n\n"
            f"6. **Technical Risks**\n"
            f"   - Top 5 technical risks\n"
            f"   - Mitigation strategies for each\n"
            f"   - Technology lock-in assessment\n"
        ),
        expected_output=(
            "A comprehensive technical architecture document in markdown format with all six "
            "sections completed. Include specific technology names, version recommendations, "
            "cost estimates in dollars, timeline in weeks, and team size recommendations."
        ),
        agent=agent,
    )


def create_mvp_spec_task(agent: Agent, idea: dict) -> Task:
    """Create an MVP specification task."""
    return Task(
        description=(
            f"Create a detailed MVP (Minimum Viable Product) specification for: "
            f"{idea.get('title', 'N/A')}\n\n"
            f"Description: {idea.get('description', 'N/A')}\n\n"
            f"Define:\n"
            f"- Core features (must-have for launch)\n"
            f"- User stories with acceptance criteria\n"
            f"- Database schema design\n"
            f"- API endpoint specifications\n"
            f"- UI/UX wireframe descriptions\n"
            f"- Technical dependencies\n"
            f"- Sprint plan (2-week sprints)\n"
        ),
        expected_output=(
            "A detailed MVP specification document with feature list, user stories, "
            "database schema, API specs, and a sprint-by-sprint development plan."
        ),
        agent=agent,
    )
