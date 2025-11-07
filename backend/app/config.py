from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./telemetry.db"
    S3_BUCKET: str = "your-bucket"
    S3_REGION: str = "your-region"
    SECRET_KEY: str = "your-secret-key"

    class Config:
        env_file = ".env"

settings = Settings()
