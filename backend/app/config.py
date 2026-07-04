"""
Configuration management for the AI Start-up Incubator Simulator.
Uses Pydantic Settings for type-safe environment variable loading.
"""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Resolve .env relative to this file: backend/app/config.py -> ../../.env -> project root .env
_ENV_FILE = str(Path(__file__).resolve().parent.parent.parent / ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_name: str = "AI Start-up Incubator Simulator"
    app_version: str = "1.0.0"
    debug: bool = False
    bypass_auth: bool = Field(default=False, description="Bypass all auth/RBAC — dev mode")
    environment: str = Field(default="development", description="development | staging | production")
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # ── LLM Providers (NVIDIA NIM API) ─────────────────────────────
    # Key 1: Nemotron Ultra + Llama 3.3 70B
    nvidia_api_key_1: str = Field(default="", description="NVIDIA API key for Nemotron Ultra & Llama 3.3")
    # Key 2: DeepSeek V4 Flash + Qwen3
    nvidia_api_key_2: str = Field(default="", description="NVIDIA API key for DeepSeek V4 & Qwen3")
    # Key 3: Nemotron Nano VL 8B
    nvidia_api_key_3: str = Field(default="", description="NVIDIA API key for Nemotron Nano VL")

    nvidia_base_url: str = Field(default="https://integrate.api.nvidia.com/v1", description="NVIDIA NIM API base URL")

    nvidia_primary_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    nvidia_fast_model: str = "meta/llama-3.3-70b-instruct"
    nvidia_reasoning_model: str = "deepseek-ai/deepseek-v4-flash"
    nvidia_compact_model: str = "qwen/qwen3-next-80b-a3b-instruct"
    nvidia_vision_model: str = "nvidia/llama-3.1-nemotron-nano-vl-8b-v1"

    llm_provider: str = Field(default="nvidia", description="Primary LLM provider: nvidia")
    llm_request_timeout: int = 120
    llm_max_retries: int = 3
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096

    # ── Security & Authentication ────────────────────────────────
    jwt_secret_key: str = Field(default="fallback-secret-key-change-in-prod", description="Secret key for JWTs")
    jwt_expiry_hours: int = Field(default=24, description="JWT expiry in hours")

    # ── Supabase (Kept for compatibility with other env vars if any) ──
    supabase_url: str = Field(default="", description="Supabase project URL")
    supabase_anon_key: str = Field(default="", description="Supabase anon/public key")
    supabase_service_role_key: str = Field(default="", description="Supabase service role key (server-side)")

    # ── Search / Tools ───────────────────────────────────────────
    tavily_api_key: str = Field(default="", description="Tavily search API key")
    serp_api_key: str = Field(default="", description="SerpAPI key (alternative)")

    # ── Agent Configuration ──────────────────────────────────────
    agent_max_iterations: int = 10
    agent_verbose: bool = True
    crew_memory: bool = True
    crew_cache: bool = True

    # ── Workflow Configuration ───────────────────────────────────
    workflow_max_iterations: int = 5
    quality_threshold: float = 0.7
    workflow_checkpoint_enabled: bool = True

    # ── Simulation Configuration ─────────────────────────────────
    simulation_max_rounds: int = 8
    num_investor_agents: int = 3

    # ── Redis / Caching ──────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    # ── Rate Limiting ────────────────────────────────────────────
    rate_limit_rpm: int = Field(default=60, description="API requests per minute per IP")

    # ── Stripe Billing ───────────────────────────────────────────
    stripe_secret_key: str = Field(default="", description="Stripe secret key")
    stripe_webhook_secret: str = Field(default="", description="Stripe webhook signing secret")
    stripe_price_pro: str = Field(default="", description="Stripe Price ID for Pro tier")
    stripe_price_enterprise: str = Field(default="", description="Stripe Price ID for Enterprise tier")

    # ── Monitoring ───────────────────────────────────────────────
    sentry_dsn: str = Field(default="", description="Sentry DSN for error tracking")

    # ── SMTP / Mailer ────────────────────────────────────────────
    smtp_host: str = Field(default="", description="SMTP host server")
    smtp_port: int = Field(default=465, description="SMTP port")
    smtp_username: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    smtp_from_email: str = Field(default="noreply@ai-incubator.com", description="From email address")
    frontend_url: str = Field(default="http://localhost:3000", description="Frontend base URL for links")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def primary_llm_key(self) -> str:
        return self.nvidia_api_key_1

    @property
    def has_nvidia(self) -> bool:
        return bool(self.nvidia_api_key_1 or self.nvidia_api_key_2 or self.nvidia_api_key_3)

    def get_api_key_for_model(self, model: str) -> str:
        """Return the correct API key for a given model name."""
        # Key 1: Nemotron Ultra + Llama 3.3
        if model in (self.nvidia_primary_model, self.nvidia_fast_model):
            return self.nvidia_api_key_1
        # Key 2: DeepSeek V4 + Qwen3
        if model in (self.nvidia_reasoning_model, self.nvidia_compact_model):
            return self.nvidia_api_key_2
        # Key 3: Nemotron Nano VL
        if model == self.nvidia_vision_model:
            return self.nvidia_api_key_3
        # Fallback to key 1
        return self.nvidia_api_key_1

    @property
    def has_tavily(self) -> bool:
        return bool(self.tavily_api_key)

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — loaded once per process."""
    return Settings()
