from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ALLOWED_ORIGINS: str = "*"
    FIREBASE_PROJECT_ID: str = "your-project-id"
    GOOGLE_APPLICATION_CREDENTIALS: str = "/app/service_account.json"
    SEND_EMAILS: bool = False
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USER: str | None = None
    SMTP_PASS: str | None = None

settings = Settings()
