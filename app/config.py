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
    SMTP_FROM: str = "noreply@apexelementgrp.com"
    SMTP_FROM_NAME: str = "APEX Element Group"  # display name shown in inboxes
    SMTP_REPLY_TO: str = ""  # defaults to SMTP_FROM

    # --- Landlord-app protection (Cloudflare Access) -----------------------
    # When enabled, every landlord API request must carry a valid Cloudflare
    # Access JWT (Cf-Access-Jwt-Assertion header / CF_Authorization cookie).
    # This closes the "hit the Railway URL directly" bypass.
    CLOUDFLARE_ACCESS_ENABLED: bool = False
    CF_ACCESS_TEAM_DOMAIN: str = ""  # e.g. noisy-bread-d22c.cloudflareaccess.com
    CF_ACCESS_AUD: str = ""  # Application Audience (AUD) tag of the landlord Access app
    # Optional extra allow-list (comma separated). Empty = trust the Access policy.
    CF_ACCESS_ALLOWED_EMAILS: str = ""

    # --- Customer-facing site ---------------------------------------------
    # Hostnames that serve ONLY the public tour site + /api/v1/public/*.
    # Landlord APIs and API docs return 404 on these hosts.
    PUBLIC_HOSTS: str = "apexelementgrp.com,www.apexelementgrp.com,tours.apexelementgrp.com"
    # Base URL used in links sent to prospects (listing pages, tour forms).
    PUBLIC_SITE_URL: str = "https://tours.apexelementgrp.com"
    # Base URL of the landlord app, for links in landlord notifications.
    LANDLORD_APP_URL: str = "https://dev-app.apexelementgrp.com"

    # --- Notifications ------------------------------------------------------
    # Where new tour requests are announced. Email falls back to the first
    # CF_ACCESS_ALLOWED_EMAILS address when unset.
    LANDLORD_NOTIFY_EMAIL: str = ""
    LANDLORD_SMS_NUMBER: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def public_hosts_list(self) -> list[str]:
        return [h.strip().lower() for h in self.PUBLIC_HOSTS.split(",") if h.strip()]

    @property
    def landlord_notify_email(self) -> str:
        if self.LANDLORD_NOTIFY_EMAIL.strip():
            return self.LANDLORD_NOTIFY_EMAIL.strip()
        allowed = self.access_allowed_emails_list
        return allowed[0] if allowed else ""

    @property
    def access_allowed_emails_list(self) -> list[str]:
        return [e.strip().lower() for e in self.CF_ACCESS_ALLOWED_EMAILS.split(",") if e.strip()]


settings = Settings()
