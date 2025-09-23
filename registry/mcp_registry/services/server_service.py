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

    def load_servers_and_state(self):
        """Load server definitions and persisted state from disk."""
        logger.info(f"2Loading server definitions from {settings.servers_dir}...")

        # Create servers directory if it doesn't exist
        settings.servers_dir.mkdir(parents=True, exist_ok=True)

        temp_servers = {}
        server_files = list(settings.servers_dir.glob("**/*.json"))
        logger.info(f"2Found {len(server_files)} JSON files in {settings.servers_dir} and its subdirectories")

        if not server_files:
            logger.warning(f"2No server definition files found in {settings.servers_dir}. Initializing empty registry.")
            self.registered_servers = {}

        for server_file in server_files:
            if server_file.name == settings.state_file_path.name:
                continue  # 상태 파일은 건너뜀

            try:
                with open(server_file, "r") as f:
                    server_info = json.load(f)

                    if (
                            isinstance(server_info, dict)
                            and "id" in server_info
                            and "name" in server_info
                    ):
                        server_id = server_info["id"]
                        if server_id in temp_servers:
                            logger.warning(f"2Duplicate server path found in {server_file}: {server_id}. Overwriting previous definition.")

                        server_info["id"] = server_info.get("id", "")
                        server_info["name"] = server_info.get("name", "")
                        server_info["version"] = server_info.get("version", "1.0")
                        server_info["description"] = server_info.get("description", "")
                        server_info["status"] = server_info.get("status", "active")
                        server_info["type"] = server_info.get("type", "")
                        server_info["scope"] = server_info.get("scope", "external")
                        server_info["migrationStatus"] = server_info.get("migrationStatus", "none")
                        server_info["serverUrl"] = server_info.get("serverUrl", "")
                        server_info["protocol"] = server_info.get("protocol", "http")
                        server_info["security"] = server_info.get("security", {})
                        server_info["supportedFormats"] = server_info.get("supportedFormats", [])
                        server_info["tags"] = server_info.get("tags", [])
                        server_info["environment"] = server_info.get("environment", "production")
                        server_info["tool_list"] = server_info.get("tool_list", [])
                        server_info["path"] = server_info.get("path", "")

                        temp_servers[server_id] = server_info
                    else:
                        logger.warning(f"2Invalid server entry format found in {server_file}. Skipping.")
            except FileNotFoundError:
                logger.error(f"2Server definition file {server_file} reported by glob not found.")
            except json.JSONDecodeError as e:
                logger.error(f"2Could not parse JSON from {server_file}: {e}.")
            except Exception as e:
                logger.error(f"2An unexpected error occurred loading {server_file}: {e}", exc_info=True)

        self.registered_servers = temp_servers
        logger.info(f"Successfully2loaded {len(self.registered_servers)} server definitions.")

        # Load persisted service state
        self._load_service_state()

    def _load_service_state(self):
        """Load persisted service state from disk."""
        logger.info(f"Attempting to load persisted state from {settings.state_file_path}...")
        loaded_state = {}

        try:
            if settings.state_file_path.exists():
                with open(settings.state_file_path, "r") as f:
                    loaded_state = json.load(f)
                if not isinstance(loaded_state, dict):
                    logger.warning(
                        f"Invalid state format in {settings.state_file_path}. Expected a dictionary. Resetting state.")
                    loaded_state = {}
                else:
                    logger.info("Successfully loaded persisted state.")
            else:
                logger.info(f"No persisted state file found at {settings.state_file_path}. Initializing state.")
        except json.JSONDecodeError as e:
            logger.error(f"Could not parse JSON from {settings.state_file_path}: {e}. Initializing empty state.")
            loaded_state = {}
        except Exception as e:
            logger.error(f"Failed to read state file {settings.state_file_path}: {e}. Initializing empty state.",
                         exc_info=True)
            loaded_state = {}

        # Initialize service state
        self.service_state = {}
        for path in self.registered_servers.keys():
            # Try exact match first, then try with/without trailing slash
            value = loaded_state.get(path, None)
            if value is None:
                if path.endswith('/'):
                    # Try without trailing slash
                    value = loaded_state.get(path.rstrip('/'), False)
                else:
                    # Try with trailing slash
                    value = loaded_state.get(path + '/', False)
            self.service_state[path] = value

        logger.info(f"Initial service state loaded: {self.service_state}")


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


    def delete_tools_by_id(self, server_id: str, tool_name: str):
        """Delete a specific tool by name from tool_list inside server file using server_id."""

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

                if "tool_list" in data and isinstance(data["tool_list"], list):
                    original_len = len(data["tool_list"])
                    # tool_name 에 맞는 항목만 제거
                    data["tool_list"] = [
                        tool for tool in data["tool_list"] if tool.get("name") != tool_name
                    ]

                    if len(data["tool_list"]) < original_len:
                        # 변경 내용 저장
                        with open(file_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=4)

                        # 인메모리 데이터도 업데이트
                        server_info["tool_list"] = data["tool_list"]
                        self.registered_servers[server_id] = server_info

                        logger.info(
                            f"Deleted tool '{tool_name}' from tool_list for server id '{server_id}' in {file_path}"
                        )
                        return True
                    else:
                        logger.warning(
                            f"Tool '{tool_name}' not found in tool_list for server id '{server_id}'"
                        )
                        return False
                else:
                    logger.warning(f"No tool_list found in server file for id '{server_id}'")
                    return False
            else:
                logger.warning(f"Server file not found for id '{server_id}' at {file_path}")
                return False

        except Exception as e:
            logger.error(
                f"Failed to delete tool '{tool_name}' for id '{server_id}': {e}", exc_info=True
            )
            return False


# Global service instance
server_service = ServerService()