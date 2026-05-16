"""
Code analysis and execution tool for tech stack evaluation.
Provides safe code analysis capabilities for the Tech Architect agent.
"""

import structlog
from crewai.tools import BaseTool

logger = structlog.get_logger()


class CodeAnalysisTool(BaseTool):
    """
    Analyzes code structures, evaluates technology stacks,
    and provides technical feasibility assessments.
    """

    name: str = "code_analysis"
    description: str = (
        "Analyze technology stacks, code architectures, and technical feasibility. "
        "Use this to evaluate different tech choices, estimate complexity, "
        "and provide architectural recommendations for startup products."
    )

    def _run(self, query: str) -> str:
        """Analyze a technical query and provide structured assessment."""
        logger.info("Code analysis requested", query=query[:100])

        # This tool primarily guides the LLM to structure its analysis
        return (
            f"**Technical Analysis Request:** {query}\n\n"
            f"Please provide a structured analysis covering:\n"
            f"1. **Technology Stack Recommendation** — Best-fit technologies with justification\n"
            f"2. **Architecture Pattern** — Recommended architecture (monolith, microservices, serverless)\n"
            f"3. **Scalability Assessment** — How the proposed stack handles growth\n"
            f"4. **Development Timeline** — Estimated effort for MVP and v1\n"
            f"5. **Technical Risks** — Key risks and mitigation strategies\n"
            f"6. **Cost Estimates** — Infrastructure and development costs\n"
            f"7. **Team Requirements** — Skills and team size needed\n"
        )


class TechStackEvaluator(BaseTool):
    """Evaluates and compares technology stack options."""

    name: str = "tech_stack_evaluator"
    description: str = (
        "Compare and evaluate different technology stack options for a startup. "
        "Considers factors like cost, scalability, developer availability, "
        "time-to-market, and long-term maintainability."
    )

    def _run(self, query: str) -> str:
        """Evaluate technology stack options."""
        logger.info("Tech stack evaluation requested", query=query[:100])

        return (
            f"**Tech Stack Evaluation for:** {query}\n\n"
            f"Evaluate the following dimensions for each technology option:\n"
            f"- **Cost**: Initial and ongoing infrastructure costs\n"
            f"- **Scalability**: Horizontal/vertical scaling capabilities\n"
            f"- **Developer Pool**: Availability of developers with expertise\n"
            f"- **Time to Market**: Speed of development and deployment\n"
            f"- **Ecosystem**: Available libraries, tools, and integrations\n"
            f"- **Performance**: Expected performance characteristics\n"
            f"- **Security**: Built-in security features and best practices\n"
            f"- **Maintainability**: Long-term maintenance requirements\n"
        )
