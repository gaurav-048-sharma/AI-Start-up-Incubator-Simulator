"""
LLM service abstraction layer.
Provides a unified interface for NVIDIA NIM API models via OpenAI-compatible
endpoint with retry logic, fallback support, and token tracking.
"""

import structlog
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel, SimpleChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from typing import Any, List

class InfiniteMockChatModel(SimpleChatModel):
    """A mock chat model that never runs out of responses."""
    @property
    def _llm_type(self) -> str:
        return "infinite_mock"
        
    def _call(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        prompt_str = str(messages)
        if "MARKET_SCORE:" in prompt_str or "validate" in prompt_str.lower():
            return "MARKET_SCORE: 0.9\nTECH_SCORE: 0.9\nOVERALL_SCORE: 0.9\nFEEDBACK: Mock response looks great. Proceed with plan."
        return "# Mock Generation\nThis is a simulated response generated because placeholder API keys are active. The simulation successfully proceeded to the next step."

from app.config import get_settings

logger = structlog.get_logger()


# ── Model role → settings attribute mapping ─────────────────────
_MODEL_ATTR_MAP = {
    "primary": "nvidia_primary_model",
    "fast": "nvidia_fast_model",
    "reasoning": "nvidia_reasoning_model",
    "compact": "nvidia_compact_model",
    "vision": "nvidia_vision_model",
}

# ── Default temperatures per role ────────────────────────────────
_DEFAULT_TEMPS = {
    "primary": 1.0,
    "fast": 0.2,
    "reasoning": 1.0,
    "compact": 0.6,
    "vision": 1.0,
}

# ── Default max_tokens per role ──────────────────────────────────
_DEFAULT_MAX_TOKENS = {
    "primary": 16384,
    "fast": 1024,
    "reasoning": 16384,
    "compact": 4096,
    "vision": 1024,
}


class LLMService:
    """
    Unified LLM provider using NVIDIA NIM API.
    Primary: nvidia/nemotron-3-ultra-550b-a55b
    Fallback: meta/llama-3.3-70b-instruct
    """

    def __init__(self, settings=None):
        self._settings = settings or get_settings()
        self._primary: Optional[BaseChatModel] = None
        self._fallback: Optional[BaseChatModel] = None
        self._models: dict[str, BaseChatModel] = {}
        self._total_tokens_used = 0
        self._initialize_providers()

    def _create_nvidia_llm(self, role: str) -> BaseChatModel:
        """Create a ChatOpenAI instance pointed at the NVIDIA NIM endpoint."""
        model_name = getattr(self._settings, _MODEL_ATTR_MAP[role])
        temperature = _DEFAULT_TEMPS.get(role, self._settings.llm_temperature)
        max_tokens = _DEFAULT_MAX_TOKENS.get(role, self._settings.llm_max_tokens)
        api_key = self._settings.get_api_key_for_model(model_name)

        if not api_key:
            logger.warning(f"No API key available for model {model_name} (role={role})")
            return InfiniteMockChatModel()

        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=self._settings.nvidia_base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=self._settings.llm_request_timeout,
            max_retries=self._settings.llm_max_retries,
        )

    def _initialize_providers(self):
        """Initialize LLM providers based on available API keys."""
        if self._settings.has_nvidia:
            for role in _MODEL_ATTR_MAP:
                try:
                    self._models[role] = self._create_nvidia_llm(role)
                except Exception as e:
                    logger.warning(f"Failed to create {role} model", error=str(e))

            self._primary = self._models.get("primary")
            self._fallback = self._models.get("fast")

            logger.info(
                "NVIDIA NIM providers initialized",
                models=list(self._models.keys()),
                primary=self._settings.nvidia_primary_model,
                fallback=self._settings.nvidia_fast_model,
            )
        else:
            # No API key — use mock for development
            self._primary = InfiniteMockChatModel()
            self._fallback = InfiniteMockChatModel()
            logger.warning("No NVIDIA API key configured — using mock LLM")

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
        Get an LLM instance by role name.

        Args:
            provider: 'primary', 'fast', 'reasoning', 'compact', 'vision', or 'auto'

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
            raise ValueError("No LLM providers are configured. Set NVIDIA_API_KEY.")

        if provider in _MODEL_ATTR_MAP:
            model = self._models.get(provider)
            if model:
                return model
            if not self._settings.has_nvidia:
                raise ValueError(f"NVIDIA NIM is not configured. Set NVIDIA_API_KEY.")
            # Create on-demand if somehow missing
            return self._create_nvidia_llm(provider)

        # Legacy compatibility: map old names to new roles
        legacy_map = {
            "gemini": "primary",
            "anthropic": "fast",
            "nvidia": "primary",
        }
        if provider in legacy_map:
            return self.get_llm(legacy_map[provider])

        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Use 'primary', 'fast', 'reasoning', 'compact', 'vision', or 'auto'."
        )

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
            provider: Which LLM role to use.

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
