from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    '''
        Dictates where to get the environment vars and 
            exports the settings to be used throughout the project
    '''
    DB_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    REDIS_HOST: str = "redis-db"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str
    MEDIA_DIR: str = "shared_media"
    TEMPFS_DIR: str = "tempfs_storage"
    LOGS_DIR: str = "logs"
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        # from_attributes=True
    )

Config = Settings()