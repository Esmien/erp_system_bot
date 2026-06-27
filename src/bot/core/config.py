from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseModelConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class LoggerConfig(BaseModelConfig):
    LOG_LEVEL: str = "DEBUG"
    LOG_SERIALIZE: bool = False  # Если True, будет писать в JSON


class BotConfig(BaseModelConfig):
    BOT_TOKEN: str = ""
    BOT_HOST: str = "0.0.0.0"
    BOT_PORT: int = 8080


class Settings(BaseModelConfig):
    logger: LoggerConfig = LoggerConfig()
    bot: BotConfig = BotConfig()


settings = Settings()
