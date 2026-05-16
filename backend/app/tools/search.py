"""
Web search tool for market research and competitive analysis.
Uses Tavily API for AI-optimized search results.
"""

import structlog
from typing import Optional
from crewai.tools import BaseTool
from pydantic import Field

from app.config import get_settings

logger = structlog.get_logger()


class WebSearchTool(BaseTool):
    """
    Searches the web for market data, competitor info, industry trends,
    and other relevant startup research using Tavily API.
    """

    name: str = "web_search"
    description: str = (
        "Search the web for real-time information about markets, competitors, "
        "industry trends, technologies, regulations, and business data. "
        "Use this to gather current, factual data for startup research."
    )
    max_results: int = Field(default=5, description="Maximum number of search results")

    def _run(self, query: str) -> str:
        """Execute a web search and return formatted results."""
        settings = get_settings()

        if not settings.has_tavily:
            return self._mock_search(query)

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=settings.tavily_api_key)
            response = client.search(
                query=query,
                max_results=self.max_results,
                search_depth="advanced",
                include_answer=True,
                include_raw_content=False,
            )

            # Format results
            results = []
            if response.get("answer"):
                results.append(f"**Summary:** {response['answer']}\n")

            for i, result in enumerate(response.get("results", []), 1):
                results.append(
                    f"**[{i}] {result.get('title', 'Untitled')}**\n"
                    f"URL: {result.get('url', 'N/A')}\n"
                    f"{result.get('content', 'No content available.')}\n"
                )

            output = "\n---\n".join(results)
            logger.info("Web search completed", query=query[:50], num_results=len(response.get("results", [])))
            return output

        except Exception as e:
            logger.error("Web search failed", query=query[:50], error=str(e))
            return f"Search failed: {str(e)}. Using available knowledge to provide analysis."

    def _mock_search(self, query: str) -> str:
        """Provide simulated search results when Tavily API is not configured."""
        logger.info("Using mock search (Tavily API not configured)", query=query[:50])
        return (
            f"**Web Search Results for:** {query}\n\n"
            f"Note: Live search is not configured. Using AI knowledge base.\n"
            f"The AI agent will use its training data to provide analysis on this topic.\n"
            f"For real-time data, configure TAVILY_API_KEY in your environment."
        )


class CompetitorSearchTool(BaseTool):
    """Specialized search tool for finding and analyzing competitors."""

    name: str = "competitor_search"
    description: str = (
        "Search for competitors in a specific market or industry. "
        "Returns information about competing companies, their products, "
        "funding, market share, and differentiators."
    )

    def _run(self, query: str) -> str:
        """Search for competitor information."""
        search_tool = WebSearchTool(max_results=8)
        competitor_query = f"competitors {query} startup companies market share funding"
        return search_tool._run(competitor_query)


class TrendSearchTool(BaseTool):
    """Specialized search tool for market trends and industry analysis."""

    name: str = "trend_search"
    description: str = (
        "Search for current market trends, emerging technologies, "
        "and industry forecasts. Returns trend data, growth projections, "
        "and market dynamics information."
    )

    def _run(self, query: str) -> str:
        """Search for trend information."""
        search_tool = WebSearchTool(max_results=8)
        trend_query = f"market trends 2025 2026 {query} growth forecast industry analysis"
        return search_tool._run(trend_query)
