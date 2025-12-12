"""Application configuration using Pydantic Settings."""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FilterRules(BaseSettings):
    """Configurable rules for filtering chat messages before summarization."""

    model_config = SettingsConfigDict(env_prefix="FILTER_")

    remove_system_messages: bool = Field(
        default=True,
        description="Remove system-generated messages from the transcript",
    )
    remove_agent_signatures: bool = Field(
        default=True,
        description="Remove agent signature blocks from messages",
    )
    min_message_length: int = Field(
        default=3,
        description="Minimum message length to include (skip very short messages)",
    )
    remove_patterns: list[str] = Field(
        default_factory=lambda: [
            r"^\s*$",  # Empty messages
            r"^(hi|hello|hey|thanks|thank you|bye|goodbye)\.?$",  # Simple greetings (optional)
        ],
        description="Regex patterns for messages to exclude",
    )
    include_greetings: bool = Field(
        default=True,
        description="If False, generic greetings will be filtered out",
    )


class Settings(BaseSettings):
    """Main application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")

    # CORS settings
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins",
    )

    # LiveChat API credentials
    livechat_client_id: str = Field(
        ...,
        description="LiveChat OAuth Client ID",
    )
    livechat_client_secret: str = Field(
        ...,
        description="LiveChat OAuth Client Secret",
    )
    livechat_account_id: Optional[str] = Field(
        default=None,
        description="LiveChat Account/License ID",
    )
    livechat_webhook_secret: Optional[str] = Field(
        default=None,
        description="Secret for verifying webhook signatures",
    )

    # LiveChat API URLs
    livechat_api_url: str = Field(
        default="https://api.livechatinc.com/v3.5",
        description="LiveChat API base URL",
    )
    livechat_accounts_url: str = Field(
        default="https://accounts.livechatinc.com",
        description="LiveChat Accounts URL for OAuth",
    )

    # OpenAI settings
    openai_api_key: str = Field(
        ...,
        description="OpenAI API key",
    )
    openai_model: str = Field(
        default="gpt-4-turbo-preview",
        description="OpenAI model to use for summarization",
    )
    openai_max_tokens: int = Field(
        default=1000,
        description="Maximum tokens for OpenAI response",
    )
    openai_temperature: float = Field(
        default=0.3,
        description="Temperature for OpenAI responses (lower = more focused)",
    )

    # CRM settings
    crm_endpoint_url: Optional[str] = Field(
        default=None,
        description="CRM API endpoint URL",
    )
    crm_api_key: Optional[str] = Field(
        default=None,
        description="CRM API authentication key",
    )
    crm_use_webhook: bool = Field(
        default=False,
        description="Use webhook instead of REST API for CRM",
    )
    crm_webhook_url: Optional[str] = Field(
        default=None,
        description="CRM webhook URL (if using webhook mode)",
    )
    crm_custom_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Custom headers for CRM requests",
    )

    # Feature flags
    auto_create_ticket: bool = Field(
        default=True,
        description="Automatically create ticket from chat",
    )
    auto_send_to_crm: bool = Field(
        default=True,
        description="Automatically send summary to CRM",
    )
    include_raw_transcript: bool = Field(
        default=False,
        description="Include raw transcript in CRM payload",
    )

    # Filter rules (loaded as nested config)
    @property
    def filter_rules(self) -> FilterRules:
        """Get filter rules configuration."""
        return FilterRules()


# Global settings instance
settings = Settings()

