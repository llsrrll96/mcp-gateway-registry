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
        server_id = server_info["id"]
        #
        # # Check if path already exists
        # if path in self.registered_servers:
        #     logger.error(f"Service registration failed: path '{path}' already exists")
        #     return False

        # Save to file
        if not self.save_server_to_file(server_info):
            return False

        # Add to in-memory registry and default to disabled
        self.registered_servers[server_id] = server_info
        self.service_state[server_id] = True

        # Persist state
        # self.save_service_state()

        logger.info(f"New service registered at path '{server_id}'")
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

    def get_server_info(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get server information by path."""
        return self.registered_servers.get(server_id)

    def update_server(self, server_id: str, server_info: Dict[str, Any]) -> bool:
        """Update an existing server."""
        # path -> id로 판단

        if server_id not in self.registered_servers:
            logger.error(f"Cannot update server at id '{server_id}': not found")
            return False

        # Save to file
        if not self.save_server_to_file(server_info):
            return False

        # Update in-memory registry
        self.registered_servers[server_id] = server_info
        return True

    def delete_server(self, server_id: str) -> bool:
        """Delete an existing server"""
        if server_id not in self.registered_servers:
            logger.error(f"Cannot update server at id '{server_id}': not found")
            return False

        # Delete to file
        self.delete_server_file_by_id(server_id)

        self.registered_servers.pop(server_id, None)
        self.service_state.pop(server_id, None)
        return True

    def delete_server_file_by_id(self, server_id: str) -> bool:
        """Delete server data file using server_id."""
        try:
            # 인메모리에 등록된 서버 정보 가져오기
            server_info = self.registered_servers.get(server_id)
            if not server_info:
                logger.warning(f"No registered server found with id '{server_id}'")
                return False

            # path → 파일명으로 변환
            path = server_info["path"]
            filename = self._path_to_filename(path)
            file_path = settings.servers_dir / filename

            if file_path.exists():
                file_path.unlink()  # 파일 삭제
                logger.info(f"Successfully deleted server file for id '{server_id}' at {file_path}")
                return True
            else:
                logger.warning(f"Server file not found for id '{server_id}' (path: {path}) at {file_path}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete server file for id '{server_id}': {e}", exc_info=True)
            return False

    def update_tool_list(self, server_id: str, tool_list: Optional[List[Dict]]):
        """Update the tool_list for a given server."""
        server_info = self.registered_servers.get(server_id)
        if not server_info:
            logger.warning(f"No registered server found with id '{server_id}'")
            return False
        return self.update_tool_list_by_id(server_id, tool_list)

    def update_tool_list_by_id(self, server_id: str, tool_list: Optional[List[Dict]]) -> bool:
        """Update tool_list for a given server with provided data, and save to file."""
        try:
            # 인메모리에 등록된 서버 정보 가져오기
            server_info = self.registered_servers.get(server_id)
            if not server_info:
                logger.warning(f"No registered server found with id '{server_id}'")
                return False

            # tool_list 업데이트 (없으면 빈 리스트로)
            server_info["tool_list"] = tool_list or []
            logger.info(f"Updated tool_list for {server_id}: {server_info['tool_list']}")

            # 서버 파일 경로 계산
            path = server_info["path"]
            filename = self._path_to_filename(path)
            file_path = settings.servers_dir / filename

            # 최신 데이터 파일에도 반영
            with open(file_path, "w") as f:
                json.dump(server_info, f, indent=2)

            logger.info(f"Successfully saved updated tool_list for server_id '{server_id}' at {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to update tool_list for id '{server_id}': {e}", exc_info=True)
            return False


    def delete_all_tools(self, server_id: str):
        # json 파일
        return self.delete_tool_list_by_id(server_id)

    def delete_tool_list_by_id(self, server_id: str) -> bool:
        """Clear the tool_list inside server file using server_id."""
        try:
            # 인메모리에 등록된 서버 정보 가져오기
            server_info = self.registered_servers.get(server_id)
            if not server_info:
                logger.warning(f"No registered server found with id '{server_id}'")
                return False

            # path → 파일명으로 변환
            path = server_info["path"]
            filename = self._path_to_filename(path)
            file_path = settings.servers_dir / filename

            if file_path.exists():
                # 파일 읽기 (JSON)
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # tool_list 비우기
                if "tool_list" in data:
                    data["tool_list"] = []

                    # 변경 내용 저장
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)

                    # 인메모리 데이터도 업데이트
                    server_info["tool_list"] = []
                    self.registered_servers[server_id] = server_info

                    logger.info(f"Cleared tool_list for server id '{server_id}' in {file_path}")
                    return True
                else:
                    logger.warning(f"No tool_list found in server file for id '{server_id}'")
                    return False
            else:
                logger.warning(f"Server file not found for id '{server_id}' at {file_path}")
                return False

        except Exception as e:
            logger.error(f"Failed to clear tool_list for id '{server_id}': {e}", exc_info=True)
            return False

# Global service instance
server_service = ServerService()