import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

import uuid
from pydantic import BaseModel
from typing import List, Dict, Optional

from ..services.server_service import server_service

logger = logging.getLogger(__name__)

router = APIRouter()

class AgentMetaDataRequest(BaseModel):
    agentCardUrl: Optional[str] = ""
    agentCard: Optional[dict] = {}
    type: Optional[str] = ""
    version: Optional[str] = ""
    description: Optional[str] = ""
    tags: Optional[List[str]] = []
    environment: Optional[str] = ""
    status: Optional[str] = ""
    boundMcps: Optional[List[dict]] = []

class AgentAuthRequest(BaseModel):
    authType: str
    apiKeyLocation: Optional[str] = None
    apiKeyName: Optional[str] = None
    apiKeyValue: Optional[str] = None
    bearerToken: Optional[str] = None
    basicUsername: Optional[str] = None
    basicPassword: Optional[str] = None
    oauthClientId: Optional[str] = None
    oauthClientSecret: Optional[str] = None
    oauthTokenUrl: Optional[str] = None
    oauthScope: Optional[str] = None



@router.get("/a2a", name="List A2A Agents")
async def get_all_a2a_agents():
    """Get all A2A agents"""
    logger.info(f"get_all_a2a_agents")
    all_agents = server_service.get_all_agents()

    agent_data = []
    for id, info in all_agents.items():
        entry = info.copy()
        entry['id'] = id
        agent_data.append(entry)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": agent_data
        }
    )

@router.post("/a2a", name="Create A2A Agent")
async def create_a2a_agent(
        body: AgentMetaDataRequest
):
    """Create a new A2A agent"""
    logger.info(f"create_a2a_agent")
    raw_uuid = uuid.uuid4()
    clean_uuid = str(raw_uuid).replace('-',"")

    agent_entry = {
        "id": clean_uuid,
        "agentCardUrl": body.agentCardUrl,
        "agentCard": body.agentCard,
        "type": body.type,
        "version": body.version,
        "description": body.description,
        "tags": body.tags,
        "environment": body.environment,
        "status": body.status,
        "boundMcps": body.boundMcps
    }

    success = server_service.register_agent(agent_entry)

    if not success:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": f"Service failed to save"},
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "data": agent_entry,
            "message": "A2A agent created successfully"
        },
    )

@router.get("/a2a/{agent_id}", name="Get A2A Agent")
async def get_all_a2a_agents(
    agent_id: str
):
    """Get a specific A2A agent by ID"""
    logger.info(f"get_all_a2a_agents")

    agent_info = server_service.get_agent_info(agent_id)
    logger.info(f"get_server_details: {agent_info}")
    if not agent_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "Agent id not registered"
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": agent_info
        }
    )

@router.put("/a2a/{agent_id}", name="Update A2A Agent")
async def update_a2a_agent(
    agent_id: str,
    body: AgentMetaDataRequest
):
    """Update an existing A2A agent"""
    logger.info(f"update_a2a_agent")
    agent_info = server_service.get_agent_info(agent_id)
    logger.info(f"get_server_details: {agent_info}")
    if not agent_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "Agent id not registered"
            }
        )

    updated_agent_entry = {
        "id": agent_id,
        "agentCardUrl": body.agentCardUrl,
        "agentCard": body.agentCard,
        "type": body.type,
        "version": body.version,
        "description": body.description,
        "tags": body.tags,
        "environment": body.environment,
        "status": body.status,
        "boundMcps": body.boundMcps
    }
    success = server_service.update_agent(agent_id, updated_agent_entry)
    if not success:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Failed to save updated agent data"
            }
        )

    logger.info(f"agent '{body.agentCardUrl}' ({agent_info["id"]}) updated '")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": updated_agent_entry,
            "message": "A2A agent updated successfully"
        }
    )
@router.delete("/a2a/{agent_id}", name="Delete A2A Agent")
async def delete_a2a_agent(
    agent_id: str
):
    """Delete an A2A agent"""
    logger.info(f"delete_a2a_agent")
    agent_info = server_service.get_agent_info(agent_id)
    if not agent_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "Service id not registered"
            }
        )

    success = server_service.delete_agent(agent_id)
    if not success:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Failed to deleted agent"
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Agent deleted successfully"
        }
    )


# auth
@router.post("/a2a/{agent_id}/auth", name="Update A2A Agent")
async def update_a2a_agent(
    agent_id: str,
    body: AgentAuthRequest
):
    """Update an auth of A2A agent"""
    agent_info = server_service.get_agent_info(agent_id)
    if not agent_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "Service id not registered"
            }
        )

    updated_agent_auth = {
        "id": agent_id,
        "authType": body.authType,
        "apiKeyLocation": body.apiKeyLocation,
        "apiKeyName": body.apiKeyName,
        "apiKeyValue": body.apiKeyValue,
        "bearerToken": body.bearerToken,
        "basicUsername": body.basicUsername,
        "basicPassword": body.basicPassword,
        "oauthClientId": body.oauthClientId,
        "oauthClientSecret": body.oauthClientSecret,
        "oauthTokenUrl": body.oauthTokenUrl,
        "oauthScope": body.oauthScope
    }
    success = server_service.update_auth(agent_id, updated_agent_auth)
    if not success:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Failed to save updated agent auth"
            }
        )

    logger.info(f"agent {agent_id} auth updated'")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": updated_agent_auth,
            "message": "A2A agent auth updated successfully"
        }
    )

@router.get("/a2a/{agent_id}/auth", name="Retrieve A2A Agent auth")
async def get_a2a_agent_auth(
    agent_id: str
):
    """Get A2A agent auth"""
    agent_auth_info = server_service.get_agent_auth_info_file(agent_id)
    logger.info(f"get_server_details: {agent_auth_info}")
    if not agent_auth_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "Agent auth not registered"
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": agent_auth_info
        }
    )
@router.delete("/a2a/{agent_id}/auth", name="Delete A2A Agent auth")
async def delete_a2a_agent_auth(
    agent_id: str
):
    """delete_a2a_agent_auth"""
    agent_auth_info = server_service.get_agent_auth_info_file(agent_id)
    logger.info(f"get_server_details: {agent_auth_info}")
    if not agent_auth_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "Agent auth id not registered"
            }
        )

    success = server_service.delete_agent_auth(agent_id)
    if not success:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Failed to deleted Agent auth"
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Agent auth deleted successfully"
        }
    )