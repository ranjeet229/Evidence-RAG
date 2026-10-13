from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    mongo_uri: str = ''
    mongo_database: str = 'evidence_rag'
    model_provider: str = 'gemini'
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-3.5-flash-lite'
    max_upload_mb: int = 10
    cors_origins: str = 'http://localhost:5173'
    auth_secret: str = ''
    auth_token_hours: int = 168

settings = Settings()
