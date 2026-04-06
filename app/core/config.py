from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DB
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Redis
    REDIS_URL: str
    RATE_LIMIT_MAX_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Cookies
    COOKIE_SECURE: bool
    COOKIE_SAMESITE: str
    COOKIE_DOMAIN: str

    class Config:
        env_file = ".env"


settings = Settings() # type: ignore
