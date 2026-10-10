import os
from pathlib import Path
from pydantic import BaseModel, Field

class Settings(BaseModel):
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "deterministic_demo"))
    llm_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gemini-1.5-flash"))
    llm_api_key: str = Field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    
    # Database: supports SQLite out of the box and PostgreSQL when provided
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///atlas.db")
    )
    
    # Resource limits and execution constraints (Blueprint page 4 & 10)
    max_upload_mb: int = Field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_MB", "25")))
    max_agent_steps: int = Field(default_factory=lambda: int(os.getenv("MAX_AGENT_STEPS", "8")))
    max_tool_retries: int = Field(default_factory=lambda: int(os.getenv("MAX_TOOL_RETRIES", "2")))
    max_result_rows: int = Field(default_factory=lambda: int(os.getenv("MAX_RESULT_ROWS", "500")))
    tool_timeout_seconds: int = Field(default_factory=lambda: int(os.getenv("TOOL_TIMEOUT_SECONDS", "30")))
    enable_semantic_memory: bool = Field(default_factory=lambda: os.getenv("ENABLE_SEMANTIC_MEMORY", "false").lower() == "true")
    enable_modeling: bool = Field(default_factory=lambda: os.getenv("ENABLE_MODELING", "true").lower() == "true")
    
    # Base storage directories
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", "data/uploads"))

    def init_dirs(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.init_dirs()
