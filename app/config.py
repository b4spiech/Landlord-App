from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://pm_user:pm_pass@localhost:5432/property_mgmt"
    PORT: int = 8000
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:8000"

    DOCUSIGN_ACCOUNT_ID: str = ""
    DOCUSIGN_API_KEY: str = ""
    DOCUSIGN_USER_ID: str = ""
    DOCUSIGN_BASE_URL: str = "https://demo.docusign.net/restapi"
    DOCUSIGN_WEBHOOK_SECRET: str = ""

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
