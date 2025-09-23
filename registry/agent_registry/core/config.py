import secrets
from pathlib import Path
from pydantic_settings import BaseSettings





class Settings(BaseSettings):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    container_registry_dir: Path = Path("/app/registry/agent_registry")
    @property
    def agents_dir(self) -> Path:
        if self.is_local_dev:
            return Path.cwd() / "registry" / "agent_registry" / "servers" # 기존: Path.cwd() / "registry" / "servers"
        return self.container_registry_dir / "servers"









# Global settings instance
settings = Settings()