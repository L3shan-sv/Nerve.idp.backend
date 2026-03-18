from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "nerve.idp"
    environment: str = "development"
    log_level: str = "debug"
    cors_origins: list[str] = ["http://localhost:5173"]
    service_name: str = "service"
    port: int = 8000

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "nerve"
    postgres_user: str = "nerve"
    postgres_password: str = "nerve_secret"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    redis_url: str = "redis://localhost:6379/0"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "nerve_neo4j"
    vault_addr: str = "http://localhost:8200"
    vault_token: str = "root"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    opa_url: str = "http://localhost:8181"
    temporal_host: str = "localhost"
    temporal_port: int = 7233
    temporal_namespace: str = "nerve-idp"
    anthropic_api_key: str = ""
    github_token: str = ""
    github_org: str = ""
    prometheus_url: str = "http://localhost:9090"
    gateway_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()

