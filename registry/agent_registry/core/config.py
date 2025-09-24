import secrets
from pathlib import Path
from pydantic_settings import BaseSettings





class Settings(BaseSettings):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    container_registry_dir: Path = Path("/app/registry/agent_registry")

    # Local development mode detection
    @property
    def is_local_dev(self) -> bool:
        """Check if running in local development mode."""
        return not Path("/app").exists()

    @property
    def agents_dir(self) -> Path:
        if self.is_local_dev:
            return Path.cwd() / "registry" / "agent_registry" / "servers" # 기존: Path.cwd() / "registry" / "servers"
        return self.container_registry_dir / "servers"

    @property
    def agents_auth_dir(self) -> Path:
        if self.is_local_dev:
            return Path.cwd() / "registry" / "agent_registry" / "servers" / "auth" # 기존: Path.cwd() / "registry" / "servers"
        return self.container_registry_dir / "servers" / "auth"

    @property
    def state_file_path(self) -> Path:
        return self.agents_dir / "server_state.json"







# Global settings instance
settings = Settings()