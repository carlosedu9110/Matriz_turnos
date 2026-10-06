"""Configuración centralizada de la aplicación mediante variables de entorno."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Matriz Turnos"
    app_env: str = "development"
    debug: bool = True

    # Base de datos
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "matriz_user"
    db_password: str = "change-me"
    db_name: str = "matriz_turnos"
    database_url: str | None = None

    # Seguridad / JWT
    secret_key: str = "change-this-secret-key-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Construye la URI de conexión SQLAlchemy, priorizando DATABASE_URL si se define."""
        if self.database_url:
            return self.database_url
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia cacheada de la configuración."""
    return Settings()


settings = get_settings()
