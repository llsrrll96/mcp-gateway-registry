
import json
import logging
from typing import Dict, List, Any, Optional

from ..core.config import settings

logger = logging.getLogger(__name__)

class ServerService:

    def __init__(self):
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_state: Dict[str, bool] = {}  # enabled/disabled state

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
        logger.info(f"***********************save_server_to_file,agent_info: {agent_info}")
        try:
            # Create servers directory if it doesn't exist
            settings.agents_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename based on path
            agent_id = agent_info["id"]
            filename = self._agent_id_to_filename(agent_id)
            file_path = settings.agents_dir / filename

            with open(file_path, "w") as f:
                json.dump(agent_info, f, indent=2)

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
        """Get server information by path."""
        return self.registered_agents.get(agent_id)











# Global service instance
server_service = ServerService()