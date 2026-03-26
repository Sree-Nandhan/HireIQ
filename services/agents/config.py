from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    agent_service_port: int = 8001
    environment: str = "development"

    # LangSmith tracing — set LANGCHAIN_TRACING_V2=true to enable
    langchain_tracing_v2: str = "false"
    langchain_api_key: str = ""
    langchain_project: str = "hireiq"

    class Config:
        env_file = ".env"


settings = Settings()
