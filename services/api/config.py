from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@db:5432/hireiq"
    agent_service_url: str = "http://agent-service:8001"
    anthropic_api_key: str = ""
    environment: str = "development"
    # Google OAuth
    google_client_id: str = ""
    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
