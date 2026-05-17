"""
Configuration management for the AI Start-up Incubator Simulator.
Uses Pydantic Settings for type-safe environment variable loading.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file="../../.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_name: str = "AI Start-up Incubator Simulator"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = Field(default="development", description="development | staging | production")
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # ── LLM Providers ────────────────────────────────────────────
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 4096

    anthropic_api_key: str = Field(default="", description="Anthropic API key (fallback)")
    anthropic_model: str = "claude-sonnet-4-20250514"

    llm_provider: str = Field(default="openai", description="Primary LLM provider: openai | anthropic")
    llm_request_timeout: int = 120
    llm_max_retries: int = 3

    # ── Supabase ─────────────────────────────────────────────────
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
        if self.llm_provider == "anthropic":
            return self.anthropic_api_key
        return self.openai_api_key

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

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
