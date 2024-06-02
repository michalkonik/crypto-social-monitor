import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


class AuthConfig(BaseSettings):
    JWT_ALG: str
    JWT_SECRET: str
    JWT_EXP: int = 5  # minutes

    REFRESH_TOKEN_KEY: str = "refreshToken"
    REFRESH_TOKEN_EXP: int = 60 * 60 * 24 * 21  # 21 days

    SECURE_COOKIES: bool = True


# Load the .env file
load_dotenv()
# Create an instance of the AuthConfig class
auth_config = AuthConfig(
    JWT_ALG=os.getenv("JWT_ALG"),
    JWT_SECRET=os.getenv("JWT_SECRET"),
)
