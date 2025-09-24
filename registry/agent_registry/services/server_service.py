from pathlib import Path
import json
import logging
from typing import Dict, List, Any, Optional

from ..core.config import settings

logger = logging.getLogger(__name__)

class ServerService:

    def __init__(self):
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.registered_agents_auth: Dict[str, Dict[str, Any]] = {}
        self.agent_state: Dict[str, bool] = {}  # enabled/disabled state


    def load_agents_and_state(self):
        """Load agent definitions and persisted state from disk."""
        logger.info(f"Loading agent definitions from {settings.agents_dir}...")

        # Create agents directory if it doesn't exist
        settings.agents_dir.mkdir(parents=True, exist_ok=True)

        temp_agents = {}
        agent_files = list(settings.agents_dir.glob("**/*.json"))
        logger.info(f"2Found {len(agent_files)} JSON files in {settings.agents_dir} and its subdirectories")

        if not agent_files:
            logger.warning(f"2No server definition files found in {settings.agents_dir}. Initializing empty registry.")
            self.registered_agents = {}

        for agent_file in agent_files:
            if agent_file.name == settings.state_file_path.name:
                continue  # 상태 파일은 건너뜀

            try:
                with open(agent_file, "r") as f:
                    agent_info = json.load(f)

                    if (
                            isinstance(agent_info, dict)
                            and "id" in agent_info
                    ):
                        agent_id = agent_info["id"]
                        if agent_id in temp_agents:
                            logger.warning(f"2Duplicate server path found in {agent_file}: {agent_id}. Overwriting previous definition.")

                        agent_info["id"] = agent_info.get("id", "")
                        agent_info["agentCardUrl"] = agent_info.get("agentCardUrl", "")
                        agent_info["agentCard"] = agent_info.get("agentCard", {})
                        agent_info["type"] = agent_info.get("type", "")
                        agent_info["version"] = agent_info.get("version", "")
                        agent_info["description"] = agent_info.get("description", "")
                        agent_info["tags"] = agent_info.get("tags", [])
                        agent_info["environment"] = agent_info.get("environment", "")
                        agent_info["status"] = agent_info.get("status", "")
                        agent_info["boundMcps"] = agent_info.get("boundMcps", [])

                        temp_agents[agent_id] = agent_info
                    else:
                        logger.warning(f"2Invalid agent entry format found in {agent_file}. Skipping.")
            except FileNotFoundError:
                logger.error(f"agent definition file {agent_file} reported by glob not found.")
            except json.JSONDecodeError as e:
                logger.error(f"2Could not parse JSON from {agent_file}: {e}.")
            except Exception as e:
                logger.error(f"2An unexpected error occurred loading {agent_file}: {e}", exc_info=True)

        self.registered_agents = temp_agents
        logger.info(f"Successfully2loaded {len(self.registered_agents)} agent definitions.")

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
        for path in self.registered_agents.keys():
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




    def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered agents."""
        return self.registered_agents.copy()

    def register_agent(self, agent_info: Dict[str, Any]) -> bool:
        """Register a new agent."""
        agent_id = agent_info["id"]

        # Save to file
        if not self.save_agent_to_file(agent_info):
            return False

        # Add to in-memory registry and default to disabled
        self.registered_agents[agent_id] = agent_info
        self.agent_state[agent_id] = True

        # Persist state
        # self.save_service_state()

        logger.info(f"New agent registered at path '{agent_id}'")
        return True

    def save_agent_to_file(self, agent_info: Dict[str, Any]) -> bool:
        """Save agent data to individual file."""
        logger.info(f"***********************save_agent_to_file,agent_info: {agent_info}")
        try:
            # Create agents directory if it doesn't exist
            settings.agents_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename based on path
            agent_id = agent_info["id"]
            file_path = self._get_agent_file_path(agent_id)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(agent_info, f, indent=2, ensure_ascii=False)

            logger.info(f"Successfully saved agent '{agent_info['agentCardUrl']}' to {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save agent '{agent_info.get('agentCardUrl', 'UNKNOWN')}' data to {agent_id}: {e}",
                         exc_info=True)
            return False

    def _agent_id_to_filename(self, agent_id: str) -> str:
        normalized = agent_id
        if not normalized.endswith(".json"):
            normalized += ".json"
        return normalized


    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent information by path."""
        return self.registered_agents.get(agent_id)


    def update_agent(self, agent_id: str, agent_info: Dict[str, Any]) -> bool:
        """Update an existing agent."""
        if agent_id not in self.registered_agents:
            logger.error(f"Cannot update agent at id '{agent_id}': not found")
            return False

        # Save to file
        if not self.save_agent_to_file(agent_info):
            return False


        # Update in-memory registry
        self.registered_agents[agent_id] = agent_info
        return True

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an existing agent"""
        if agent_id not in self.registered_agents:
            logger.error(f"Cannot update agent at id '{agent_id}': not found")
            return False

        # Delete to file
        self.delete_agent_file_by_id(agent_id)

        self.registered_agents.pop(agent_id, None)
        self.agent_state.pop(agent_id, None)
        return True

    def delete_agent_file_by_id(self, agent_id: str) -> bool:
        """Delete agent data file using agent_id."""
        try:
            # 인메모리에 등록된 서버 정보 가져오기
            agent_info = self.registered_agents.get(agent_id)
            if not agent_info:
                logger.warning(f"No registered agent found with id '{agent_id}'")
                return False

            # id → 파일명으로 변환
            file_path = self._get_agent_file_path(agent_id)

            if file_path.exists():
                file_path.unlink()  # 파일 삭제
                logger.info(f"Successfully deleted agent file for id '{agent_id}' at {file_path}")
                return True
            else:
                logger.warning(f"agent file not found for id '{agent_id}' {file_path}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete agent file for id '{agent_id}'at {file_path}: {e}", exc_info=True)
            return False

    def _get_agent_file_path(self, agent_id: str) -> Path:
        """Get the file path for an agent ID."""
        filename = self._agent_id_to_filename(agent_id)
        return settings.agents_dir / filename

    def update_auth(self, agent_id: str, agent_auth_info: Dict[str, Any]) -> bool:
        if agent_id not in self.registered_agents:
            logger.error(f"Cannot update agent at id '{agent_id}': not found")
            return False

        # Save to file
        if not self.save_agent_auth_to_file(agent_auth_info):
            return False

        self.registered_agents_auth[agent_id] = agent_auth_info
        return True

    def save_agent_auth_to_file(self, agent_auth_info: Dict[str, Any]) -> bool:
        try:
            # Create agents auth directory if it doesn't exist
            settings.agents_auth_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename based on path
            agent_id = agent_auth_info["id"]
            file_path = self._get_agent_auth_file_path(agent_id)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(agent_auth_info, f, indent=2, ensure_ascii=False)

            logger.info(f"Successfully saved agent auth {agent_id}, {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save agent auth data to {agent_id}, {file_path}: {e}",
                         exc_info=True)
            return False

    def _get_agent_auth_file_path(self, agent_id: str) -> Path:
        """Get the file path for an agent ID."""
        filename = self._agent_id_to_filename(agent_id)
        return settings.agents_auth_dir / filename

    def get_agent_auth_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self.registered_agents_auth.get(agent_id)


# Global service instance
server_service = ServerService()