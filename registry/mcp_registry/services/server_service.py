import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from ..core.config import settings

logger = logging.getLogger(__name__)


class ServerService:
    """Service for managing server registration and state."""

    def __init__(self):
        self.registered_servers: Dict[str, Dict[str, Any]] = {}
        self.service_state: Dict[str, bool] = {}  # enabled/disabled state

    def get_all_servers(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered servers."""
        return self.registered_servers.copy()

    def register_server(self, server_info: Dict[str, Any]) -> bool:
        """Register a new server."""
        path = server_info["path"]
        #
        # # Check if path already exists
        # if path in self.registered_servers:
        #     logger.error(f"Service registration failed: path '{path}' already exists")
        #     return False

        # Save to file
        if not self.save_server_to_file(server_info):
            return False

        # Add to in-memory registry and default to disabled
        # self.registered_servers[path] = server_info
        # self.service_state[path] = False

        # Persist state
        # self.save_service_state()

        logger.info(f"New service registered at path '{path}'")
        return True


    def save_server_to_file(self, server_info: Dict[str, Any]) -> bool:
        """Save server data to individual file."""
        logger.info(f"***********************save_server_to_file,server_info: {server_info}")
        try:
            # Create servers directory if it doesn't exist
            settings.servers_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename based on path
            path = server_info["path"]
            filename = self._path_to_filename(path)
            file_path = settings.servers_dir / filename

            with open(file_path, "w") as f:
                json.dump(server_info, f, indent=2)

            logger.info(f"Successfully saved server '{server_info['name']}' to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save server '{server_info.get('name', 'UNKNOWN')}' data to {filename}: {e}",
                         exc_info=True)
            return False

    def _path_to_filename(self, path: str) -> str:
        """Convert a path to a safe filename."""
        # Remove leading slash and replace remaining slashes with underscores
        normalized = path.lstrip("/").replace("/", "_")
        # Append .json extension if not present
        if not normalized.endswith(".json"):
            normalized += ".json"
        return normalized

# Global service instance
server_service = ServerService()