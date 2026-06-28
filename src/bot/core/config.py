from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseModelConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class LoggerConfig(BaseModelConfig):
    LOG_LEVEL: str = "DEBUG"
    LOG_SERIALIZE: bool = False  # Если True, будет писать в JSON


class ApiConfig(BaseModelConfig):
    API_BASE_URL: str


class BotConfig(BaseModelConfig):
    BOT_TOKEN: str
    BOT_HOST: str = "0.0.0.0"
    BOT_PORT: int = 8080


class WebhookConfig(BaseModelConfig):
    WEBHOOK_HOST: str
    WEBHOOK_PATH: str = "/webhook"
    WEBHOOK_SECRET: str


class Settings(BaseModelConfig):
    logger: LoggerConfig = LoggerConfig()
    bot: BotConfig = BotConfig()
    webhook: WebhookConfig = WebhookConfig()
    api: ApiConfig = ApiConfig()


settings = Settings()
