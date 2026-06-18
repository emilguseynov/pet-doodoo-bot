from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Настройки приложения.

    Значения читаются из переменных окружения и файла .env.
    Pydantic проверяет, что обязательные поля заданы, при старте бота.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    bot_token: str
    database_url: str = "postgresql+asyncpg://petbot:petbot@localhost:5432/petbot"


settings = Settings()
