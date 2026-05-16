"""
LLM service abstraction layer.
Provides a unified interface for OpenAI and Anthropic with retry logic,
fallback support, and token tracking.
"""

import structlog
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.config import get_settings

logger = structlog.get_logger()


class LLMService:
    """
    Unified LLM provider with automatic fallback.
    Primary: OpenAI GPT-4o
    Fallback: Anthropic Claude
    """

    def __init__(self, settings=None):
        self._settings = settings or get_settings()
        self._primary: Optional[BaseChatModel] = None
        self._fallback: Optional[BaseChatModel] = None
        self._total_tokens_used = 0
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize LLM providers based on available API keys."""
        if self._settings.has_openai:
            self._primary = ChatOpenAI(
                model=self._settings.openai_model,
                api_key=self._settings.openai_api_key,
                temperature=self._settings.openai_temperature,
                max_tokens=self._settings.openai_max_tokens,
                request_timeout=self._settings.llm_request_timeout,
                max_retries=self._settings.llm_max_retries,
            )
            logger.info("OpenAI provider initialized", model=self._settings.openai_model)

        if self._settings.has_anthropic:
            self._fallback = ChatAnthropic(
                model=self._settings.anthropic_model,
                api_key=self._settings.anthropic_api_key,
                temperature=self._settings.openai_temperature,
                max_tokens=self._settings.openai_max_tokens,
                default_request_timeout=self._settings.llm_request_timeout,
            )
            logger.info("Anthropic provider initialized", model=self._settings.anthropic_model)

        # Swap if anthropic is the primary provider
        if self._settings.llm_provider == "anthropic" and self._fallback:
            self._primary, self._fallback = self._fallback, self._primary

        if not self._primary and not self._fallback:
            logger.warning("No LLM providers configured — agents will not function")

    def get_primary_llm(self) -> Optional[BaseChatModel]:
        """Get the primary LLM instance for CrewAI / LangGraph use."""
        return self._primary

    def get_fallback_llm(self) -> Optional[BaseChatModel]:
        """Get the fallback LLM instance."""
        return self._fallback

    def get_llm(self, provider: str = "auto") -> BaseChatModel:
        """
        Get an LLM instance by provider name.

        Args:
            provider: 'openai', 'anthropic', or 'auto' (uses primary)

        Returns:
            A configured LangChain chat model.

        Raises:
            ValueError: If the requested provider is not configured.
        """
        if provider == "auto":
            if self._primary:
                return self._primary
            if self._fallback:
                logger.warning("Primary LLM unavailable, using fallback")
                return self._fallback
            raise ValueError("No LLM providers are configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.")

        if provider == "openai":
            if not self._settings.has_openai:
                raise ValueError("OpenAI is not configured. Set OPENAI_API_KEY.")
            return ChatOpenAI(
                model=self._settings.openai_model,
                api_key=self._settings.openai_api_key,
                temperature=self._settings.openai_temperature,
                max_tokens=self._settings.openai_max_tokens,
            )

        if provider == "anthropic":
            if not self._settings.has_anthropic:
                raise ValueError("Anthropic is not configured. Set ANTHROPIC_API_KEY.")
            return ChatAnthropic(
                model=self._settings.anthropic_model,
                api_key=self._settings.anthropic_api_key,
                temperature=self._settings.openai_temperature,
                max_tokens=self._settings.openai_max_tokens,
            )

        raise ValueError(f"Unknown LLM provider: {provider}. Use 'openai', 'anthropic', or 'auto'.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        provider: str = "auto",
    ) -> str:
        """
        Generate a response from the LLM with retry and fallback.

        Args:
            prompt: The user/task prompt.
            system_prompt: Optional system message for context.
            provider: Which LLM provider to use.

        Returns:
            The generated text response.
        """
        llm = self.get_llm(provider)
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            response = await llm.ainvoke(messages)
            logger.info(
                "LLM generation completed",
                provider=provider,
                prompt_length=len(prompt),
                response_length=len(response.content),
            )
            return response.content
        except Exception as e:
            # Try fallback if primary fails
            if provider == "auto" and self._fallback:
                logger.warning("Primary LLM failed, attempting fallback", error=str(e))
                fallback_response = await self._fallback.ainvoke(messages)
                return fallback_response.content
            raise

    def get_crew_llm(self) -> BaseChatModel:
        """Get LLM configured specifically for CrewAI agents."""
        return self.get_llm("auto")

    def get_graph_llm(self) -> BaseChatModel:
        """Get LLM configured specifically for LangGraph nodes."""
        return self.get_llm("auto")

    @property
    def total_tokens_used(self) -> int:
        return self._total_tokens_used


# Module-level singleton
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the global LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
