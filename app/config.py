from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://pm_user:pm_pass@localhost:5432/property_mgmt"
    PORT: int = 8000
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:8000"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    DOCUSIGN_ACCOUNT_ID: str = ""
    DOCUSIGN_API_KEY: str = ""
    DOCUSIGN_USER_ID: str = ""
    DOCUSIGN_BASE_URL: str = "https://demo.docusign.net/restapi"
    DOCUSIGN_WEBHOOK_SECRET: str = ""
    # JWT (server-to-server) auth. Accept several env var names so existing
    # Railway config (DOCUSIGN_APP_INTEGRATION_KEY / DOCUSIGN_RSA_PRIVATE_KEY)
    # works without renaming.
    DOCUSIGN_INTEGRATION_KEY: str = Field(
        default="",
        validation_alias=AliasChoices(
            "DOCUSIGN_INTEGRATION_KEY",
            "DOCUSIGN_APP_INTEGRATION_KEY",
            "DOCUSIGN_API_KEY",
        ),
    )
    DOCUSIGN_PRIVATE_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("DOCUSIGN_PRIVATE_KEY", "DOCUSIGN_RSA_PRIVATE_KEY"),
    )
    DOCUSIGN_OAUTH_HOST: str = "account-d.docusign.com"  # demo; account.docusign.com for prod

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@apexelementgroup.com"

    CLOUDFLARE_ACCESS_ENABLED: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
