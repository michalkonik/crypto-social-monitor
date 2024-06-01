import os
import json
from typing import Any

from pydantic import PostgresDsn, RedisDsn, model_validator
from pydantic_settings import BaseSettings

from src.constants import Environment

from dotenv import load_dotenv

# Load the .env file
load_dotenv()


class Config(BaseSettings):
    DATABASE_URL: PostgresDsn
    REDIS_URL: RedisDsn

    SITE_DOMAIN: str = "myapp.com"

    ENVIRONMENT: Environment = Environment.PRODUCTION

    CORS_ORIGINS: list[str]
    CORS_ORIGINS_REGEX: str | None = None
    CORS_HEADERS: list[str]

    APP_VERSION: str = "1"

    # download database url secret from AWS param store
    #DATABASE_URL = get_param_store_secret(f"/{ENVIRONMENT}/SocialMonitor/DatabaseURL")
    DATABASE_URL = "postgresql+asyncpg://app:app@app_db/postgres"


# Create an instance of the Config class
settings = Config(
    REDIS_URL=os.getenv("REDIS_URL"),
    CORS_ORIGINS=json.loads(os.getenv("CORS_ORIGINS")),
    CORS_HEADERS=json.loads(os.getenv("CORS_HEADERS")),
)

app_configs: dict[str, Any] = {"title": "Social Monitoring API"}
if settings.ENVIRONMENT.is_deployed:
    app_configs["root_path"] = f"/v{settings.APP_VERSION}"

if not settings.ENVIRONMENT.is_debug:
    app_configs["openapi_url"] = None  # hide docs
