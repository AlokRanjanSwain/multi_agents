from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""

    # Langfuse
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_base_url: str = "http://localhost:3000"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    registry_path: str = "registry.yaml"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
