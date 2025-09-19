import os
import secrets
from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables
    )
    
    # Auth settings
    secret_key: str = ""
    admin_user: str = "admin"
    admin_password: str = "password"
    session_cookie_name: str = "mcp_gateway_session"
    session_max_age_seconds: int = 60 * 60 * 8  # 8 hours
    auth_server_url: str = "http://localhost:8888"
    auth_server_external_url: str = "http://localhost:8888"  # External URL for OAuth redirects
    
    # Embeddings settings
    embeddings_model_name: str = "all-MiniLM-L6-v2"
    embeddings_model_dimensions: int = 384
    
    # Health check settings  
    health_check_interval_seconds: int = 300  # 5 minutes for automatic background checks
    health_check_timeout_seconds: int = 2  # Very fast timeout for user-driven actions
    
    # WebSocket performance settings
    max_websocket_connections: int = 100  # Reasonable limit for development/testing
    websocket_send_timeout_seconds: float = 2.0  # Allow slightly more time per connection
    websocket_broadcast_interval_ms: int = 10  # Very responsive - 10ms minimum between broadcasts
    websocket_max_batch_size: int = 20  # Smaller batches for faster updates
    websocket_cache_ttl_seconds: int = 1  # 1 second cache for near real-time user feedback
    
    # Container paths - adjust for local development
    container_app_dir: Path = Path("/app")
#    container_registry_dir: Path = Path("/app/registry")
    container_registry_dir: Path = Path("/app/mcp_registry")
    container_log_dir: Path = Path("/app/logs")
    
    # Local development mode detection
    @property
    def is_local_dev(self) -> bool:
        """Check if running in local development mode."""
        return not Path("/app").exists()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Generate secret key if not provided
        if not self.secret_key:
            self.secret_key = secrets.token_hex(32)

    @property
    def embeddings_model_dir(self) -> Path:
        if self.is_local_dev:
            return Path.cwd() / "registry" / "models" / self.embeddings_model_name
        return self.container_registry_dir / "models" / self.embeddings_model_name

    @property
    def servers_dir(self) -> Path:
        if self.is_local_dev:
            return Path.cwd() / "mcp_registry" / "servers" # Path.cwd() / "registry" / "servers"
        return self.container_registry_dir / "servers"

    @property
    def static_dir(self) -> Path:
        if self.is_local_dev:
            return Path.cwd() / "registry" / "static"
        return self.container_registry_dir / "static"

    @property
    def templates_dir(self) -> Path:
        if self.is_local_dev:
            return Path.cwd() / "registry" / "templates"
        return self.container_registry_dir / "templates"

    @property
    def nginx_config_path(self) -> Path:
        return Path("/etc/nginx/conf.d/nginx_rev_proxy.conf")

    @property
    def state_file_path(self) -> Path:
        return self.servers_dir / "server_state.json"

    @property
    def log_file_path(self) -> Path:
        if self.is_local_dev:
            return Path.cwd() / "logs" / "registry.log"
        return self.container_log_dir / "registry.log"

    @property
    def faiss_index_path(self) -> Path:
        return self.servers_dir / "service_index.faiss"

    @property
    def faiss_metadata_path(self) -> Path:
        return self.servers_dir / "service_index_metadata_mcp.json"

    @property
    def dotenv_path(self) -> Path:
        if self.is_local_dev:
            return Path.cwd() / ".env"
        return self.container_registry_dir / ".env"


# Global settings instance
settings = Settings() 