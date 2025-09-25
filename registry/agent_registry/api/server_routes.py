import json
import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse

import uuid
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from ..services.server_service import server_service
from ..services.message_service import message_service

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

class AgentFetchCardRequest(BaseModel):
    agent_url: str

class MessageRequest(BaseModel):
    message: str


class Provider(BaseModel):
    organization: Optional[str] = Field(None, description="Provider organization")

class Skill(BaseModel):
    id: Optional[str] = Field(None, description="Unique skill id")
    name: Optional[str] = Field(None, description="Human readable skill name")
    description: Optional[str] = Field(None, description="Skill description")

class AgentAgentCardRequest(BaseModel):
    protocolVersion: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    version: Optional[str] = None
    skills: Optional[List[Skill]] = None
    provider: Optional[Provider] = None

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

@router.post("/a2a/fetch-card", name="Fetch Agent Card")
async def update_a2a_agent(
    request: AgentFetchCardRequest
):
    """Fetch an agent card from a URL"""
    # 1. Agent Card 가져오기
    agent_url = request.agent_url
    logger.info(f"Fetching Agent Card from: {agent_url}")
    result = await server_service.fetch_json(agent_url)
    if not result["success"]:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": result["success"],
                "message": result["message"]
            }
        )
    logger.info(f"Agent Card fetched successfully: {result}")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": result["data"],
            "message": "Agent card fetched successfully"
        }
    )

@router.post("/a2a/validate", name="Validate Agent Card")
async def update_a2a_agent(
        request: AgentAgentCardRequest
):
    """Validate an A2A agent card"""
    errors: List[str] = []
    warnings: List[str] = []

    # 필수 필드
    if not request.protocolVersion:
        errors.append("Protocol version is required")
    if not request.name:
        errors.append("Agent name is required")
    if not request.description:
        errors.append("Agent description is required")
    if not request.url:
        errors.append("Service endpoint URL is required")

    # 선택이지만 권장되는 필드
    if not request.skills or len(request.skills) == 0:
        warnings.append("No skills defined")
    if not request.version:
        warnings.append("Agent version not specified")
    if not (request.provider and request.provider.organization):
        warnings.append("Provider organization not specified")

    # 스킬 상세 검증
    if request.skills:
        for idx, skill in enumerate(request.skills, start=1):
            if not skill.id:
                if not skill.id:
                    errors.append(f"Skill {idx}: ID is required")
                if not skill.name:
                    errors.append(f"Skill {idx}: Name is required")
                if not skill.description:
                    errors.append(f"Skill {idx}: Description is required")

    result = {
        "success": len(errors) == 0,
        "message": errors
    }

    return JSONResponse(
        status_code=200 if result["success"] else 400,
        content=result
    )



@router.post("/a2a/{agent_id}/message", name="Send Message to Agent")
async def send_message_to_agent(
        agent_id: str,
        request: MessageRequest
):
    """Send a message to an A2A agent and get response"""

    async def generate_events():
        async for event in message_service.send_message_to_a2a_agent_stream(agent_id, request.message):
            # Server-Sent Events 형식으로 전송
            yield f"data: {json.dumps(event.dict(), default=str)}\n\n"

        # 스트림 종료
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )







    # 2. Health Check
    # logger.info("Performing health check...")
    # health_ok = await check_agent_health(agent_url)
    # if not health_ok:
    #     logger.warning("Health check failed, but continuing registration...")

    # 3. Registry에 저장
    # logger.info("Saving to registry...")
    # registration_data = await server_service.save_to_registry(agent_card_data)



# health 패키지로 이동 예정
# async def check_agent_health(agent_url: str) -> bool:
#     """Agent의 건강 상태 확인"""
#     health_endpoints = [
#         f"{agent_url}/health",
#         f"{agent_url}/api/health",
#         f"{agent_url}/api/v1/health",
#         f"{agent_url}/status"
#     ]
#
#     for endpoint in health_endpoints:
#         try:
#             async with httpx.AsyncClient(timeout=5.0) as client:
#                 response = await client.get(endpoint)
#                 if response.status_code == 200:
#                     logger.info(f"Agent health check passed: {endpoint}")
#                     return True
#
#         except (httpx.RequestError, httpx.HTTPStatusError):
#             continue
#
#     # Health endpoint가 없어도 기본 URL에 접근 가능하면 OK
#     try:
#         async with httpx.AsyncClient(timeout=5.0) as client:
#             response = await client.get(agent_url)
#             if response.status_code < 500:  # 500 이상이 아니면 기본적으로 동작한다고 판단
#                 logger.info(f"Agent basic connectivity check passed: {agent_url}")
#                 return True
#     except:
#         pass
#
#     logger.warning(f"Agent health check failed for: {agent_url}")
#     return False