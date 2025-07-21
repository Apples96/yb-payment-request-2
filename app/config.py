import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
        self.lighton_api_key: str = os.getenv("LIGHTON_API_KEY", "")
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.port: int = int(os.getenv("PORT", "8000"))
        
        # LightOn Paradigm API settings
        self.lighton_base_url: str = "https://paradigm.lighton.ai"
        self.lighton_docsearch_endpoint: str = "/api/v2/chat/document-search"
        
        # Workflow execution settings
        self.max_execution_time: int = 300  # 5 minutes
        self.max_workflow_steps: int = 50
        
    def validate(self) -> None:
        """Validate that required settings are present"""
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        if not self.lighton_api_key:
            raise ValueError("LIGHTON_API_KEY is required")

# Global settings instance
settings = Settings()