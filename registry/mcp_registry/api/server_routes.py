import json
import httpx
import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status, Cookie
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse

import uuid
from pydantic import BaseModel
from typing import List, Dict, Optional

# from ..core.config import settings
from ...auth.dependencies import web_auth, api_auth, enhanced_auth
from ..services.server_service import server_service
from ..core.config import settings
from ..services.repo_service import repo_service

logger = logging.getLogger(__name__)

router = APIRouter()

class MCPRegisterRequest(BaseModel):
    name: str
    version: Optional[str] = "1.0"
    description: Optional[str] = ""
    status: Optional[str] = "active"
    type: Optional[str] = "analysis"
    scope: Optional[str] = "external"
    migrationStatus: Optional[str] = "none"
    serverUrl: str
    protocol: Optional[str] = "http"
    security: Optional[str] = "none"
    supportedFormats: Optional[List[str]] = []
    tags: Optional[List[str]] = []
    environment: Optional[str] = "production"
    tool_list: Optional[List[dict]] = []

class MCPToolsUpdateRequest(BaseModel):
    tools: Optional[List[dict]] = []

class MCPCICDRequest(BaseModel):
    id: Optional[str] = ""
    project_full_path: str
    project_full_name: str
    status: Optional[str] = ""
    version: Optional[str] = ""
    port: Optional[str] = ""

@router.get("/mcp", name="servers")
async def get_servers_json():

    all_servers = server_service.get_all_servers()
    # {'a0d063b92a384691bc4bce3986e5f8af': == key가 id

    # path와 서버 정보를 합쳐서 리스트로 만들기
    service_data = []
    for path, info in all_servers.items():
        entry = info.copy()
        entry['path'] = path
        service_data.append(entry)


    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": service_data
        }
    )

@router.post("/mcp", name="mcp_register")
async def mcp_register_service(
        body: MCPRegisterRequest
):
    from ..search.service import faiss_service

    logger.info(f"***Name: {body.name}, URL: {body.serverUrl}")

    # 1. 최종 path 생성
    # 전체 UUID 생성
    raw_uuid = uuid.uuid4()
    clean_uuid = str(raw_uuid).replace('-',"")

    # 하이픈 기준으로 첫 번째 부분만 사용
    path = f"/{clean_uuid}"

    tag_str = ",".join(tag.strip() for tag in body.tags)
    logger.info(f"***tag_str: {tag_str}")

    # 기존 저장
    from registry.api.server_routes import register_service
    # register_service 호출 (HTTP 호출이 아니라 내부 함수 호출)
    # response: JSONResponse = await register_service(
    #     name=body.name,
    #     description=body.description,
    #     path=path,
    #     proxy_pass_url=body.serverUrl,
    #     tags=tag_str,
    #     num_tools=0,
    #     num_stars=0,
    #     is_python=False,
    #     license_str="N/A",
    #     user_context= user_context
    # )
    # if response.status_code != 201:
    #     try:
    #         body_json = json.loads(response.body.decode())
    #         message_content = body_json.get("error") if isinstance(body_json, dict) else str(body_json)
    #     except Exception:
    #         message_content = "failed to regist server"
    #     return JSONResponse(
    #         status_code=response.status_code,
    #         content={
    #             "success": False,
    #             "message": message_content
    #         }
    #     )

    server_id = clean_uuid

    # Create server entry
    server_entry = {
        "id": server_id,
        "name": body.name,
        "version": body.version,
        "description": body.description,
        "status": body.status,
        "type": body.type,
        "scope": body.scope,
        "migrationStatus": body.migrationStatus,
        "serverUrl": body.serverUrl,
        "protocol": body.protocol,
        "security": body.security,
        "supportedFormats": body.supportedFormats,
        "tags": body.tags,
        "environment": body.environment,
        "tool_list": body.tool_list,
        "path": path,
    }

    # Register the server
    success = server_service.register_server(server_entry)

    if not success:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": f"Service failed to save"},
        )

    # Add to FAISS index (disabled by default) -- X

    # Regenerate Nginx configuration

    # Broadcast health status update to WebSocket clients

    # enable true 가  default 인 과정 - active
    # from registry.api.server_routes import toggle_service_route
    # response: JSONResponse = await toggle_service_route(
    #     request=None,
    #     service_path=path,
    #     enabled="on",  # Form 데이터 대체
    #     user_context=user_context,
    # )
    # if response.status_code == 200:
    #     logger.info(f"enable 성공: {response.body.decode()}")
    #     # tool_list 를 가져와서 , servers json 에 채우기
    #
    # else:
    #     logger.error(f"enable 실패: '{response.status_code}', off 로 설정", )

    return JSONResponse(
        status_code=201,
        content={
            "success": True,
            "data": server_entry
        },
    )


@router.get("/mcp/{server_id}")
async def get_server_details(
    server_id: str,
):
    # Get servers based
    server_info = server_service.get_server_info(server_id)
    logger.info(f"get_server_details: {server_info}")
    if not server_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "Service id not registered"
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": server_info
        }
    )

@router.put("/mcp/{server_id}")
async def edit_server_submit(
    server_id: str,
    body: MCPRegisterRequest
):
    server_info = server_service.get_server_info(server_id)
    if not server_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "Service path not found"
            }
        )

    # Prepare updated server data
    updated_server_entry = {
        "id": server_id,
        "name": body.name,
        "version": body.version,
        "description": body.description,
        "status": body.status,
        "type": body.type,
        "scope": body.scope,
        "migrationStatus": body.migrationStatus,
        "serverUrl": body.serverUrl,
        "protocol": body.protocol,
        "security": body.security,
        "supportedFormats": body.supportedFormats,
        "tags": body.tags,
        "environment": body.environment,
        "tool_list": body.tool_list,
        "path": server_info["path"]
    }

    # Update server
    success = server_service.update_server(server_id, updated_server_entry)
    logger.info(f"success: {success}")
    if not success:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Failed to save updated server data"
            }
        )

    logger.info(f"Server '{body.name}' ({server_id}) updated '")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": updated_server_entry
        }
    )

@router.delete("/mcp/{server_id}")
async def edit_server_submit(
    server_id: str
):
    """Delete MCP Server Data"""
    server_info = server_service.get_server_info(server_id)
    if not server_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "Service path not found"
            }
        )

    # Delete server
    success = server_service.delete_server(server_id)
    if not success:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Failed to save updated server data"
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "MCP deleted successfully"
        }
    )

    # nginx 등은 나중에 ..


# /api/tools/{service_path}
@router.get("/mcp/{server_id}/tools")
async def get_server_tools(
    server_id: str,
):
    """Get tool list for a service"""
    # from ..core.mcp_client import mcp_client_service

    # Handle specific server case - fetch live tools from MCP server
    server_info = server_service.get_server_info(server_id)
    if not server_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "Service id not registered"
            }
        )
    # Check if service is enabled and healthy
    # is_enabled = server_service.is_service_enabled(server_id)
    # if not is_enabled:
    #     raise HTTPException(status_code=400, detail="Cannot fetch tools from disabled service")

    server_url = server_info.get("serverUrl")
    if not server_url:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Service has no server_url configured"
            }
        )

    logger.info(f"Fetching live tools for {server_id} from {server_url}")
    # try:
        # Call MCP client to fetch fresh tools using server configuration
        # MCP 서버에서 최신 툴 목록을 가져와서 레지스트리 갱신
        # tool_list = await mcp_client_service.get_tools_from_server_with_server_info(server_url, server_info)
        # if tool_list is None:
        #     return JSONResponse(
        #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #         content={
        #             "success": False,
        #             "message": "Failed to fetch tools from MCP server. Service may be unhealthy."
        #         }
        #     )
    tool_list = server_info.get("tool_list")


    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": tool_list
        }
    )

@router.post("/mcp/{server_id}/tools")
async def update_server_tools(
    server_id: str,
    body: MCPToolsUpdateRequest
):
    """Update tool list for a service"""
    server_info = server_service.get_server_info(server_id)
    if not server_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "Service id not registered"
            }
        )

    success = server_service.update_tool_list(server_id, body.tools)
    if not success:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Failed to updated tools data"
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "MCP tools saved successfully"
        }
    )


@router.delete("/mcp/{server_id}/tools")
async def delete_all_tools(
    server_id: str
):
    """Delete all tool list for a service"""
    server_info = server_service.get_server_info(server_id)
    if not server_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "Service id not registered"
            }
        )

    success = server_service.delete_all_tools(server_id)
    if not success:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Failed to deleted tools data"
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "All MCP tools deleted successfully"
        }
    )

@router.delete("/mcp/{server_id}/tools/{tool_name}")
async def delete_all_tools(
    server_id: str,
    tool_name: str
):
    """Delete a specific tool from an MCP"""
    server_info = server_service.get_server_info(server_id)
    if not server_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "Service id not registered"
            }
        )

    success = server_service.delete_tools_by_id(server_id, tool_name)
    if not success:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Failed to updated tools data"
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "MCP tool deleted successfully"
        }
    )

@router.post("/mcp/build", name="MCP CI")
async def mcp_build(
        request: MCPCICDRequest
):
    str_uuid = str(uuid.uuid4())

    headers = {"Content-Type": "application/json"}
    payload = {
        "id": str_uuid,
        "project_full_path": request.project_full_path,
        "project_full_name": request.project_full_name
    }

    # 비동기 호출
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(settings.CI_BUILD_URL, json=payload, headers=headers)
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except httpx.HTTPStatusError as e:
            return {"status": "error", "detail": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

# 배포 테스트용
@router.post("/mcp/deploy", name="MCP CD")
async def mcp_deploy(
        request: MCPCICDRequest
):
    str_uuid = str(uuid.uuid4())

    headers = {"Content-Type": "application/json"}
    payload = {
        "id": str_uuid,
        "project_full_path": request.project_full_path,
        "project_full_name": request.project_full_name,
        "version": request.version
    }

    # 비동기 호출
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(settings.CD_BUILD_URL, json=payload, headers=headers)
            response.raise_for_status()
            return {"status": True, "data": response.json()}
        except httpx.HTTPStatusError as e:
            return {"status": False, "message": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"status": False, "message": str(e)}

@router.post("/mcp/callbacks/ci", name="MCP CI Callback")
async def mcp_build_callback(
        request: MCPCICDRequest
):
    """Callback endpoint for CI build status"""
    logger.info(f"[CI CALLBACK] ID={request.id}, "
                f"Project={request.project_full_name} ({request.project_full_path}), "
                f"Status={request.status}, Version={request.version}")

    headers = {"Content-Type": "application/json"}
    payload = {
        "id": request.id,
        "project_full_path": request.project_full_path,
        "project_full_name": request.project_full_name,
        "status": request.status,
        "version": request.version
    }

    # 배포서버에게 배포 요청
    # 비동기 호출
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(settings.CI_BUILD_URL, json=payload, headers=headers)
            response.raise_for_status()
            return {"status": True, "data": response.json()}
        except httpx.HTTPStatusError as e:
            return {"status": False, "message": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"status": False, "message": str(e)}


@router.post("/mcp/callbacks/cd", name="MCP CD Callback")
async def mcp_deploy_callback(
        request: MCPCICDRequest
):
    """Callback endpoint for CI build status"""
    logger.info(f"[CI CALLBACK] ID={request.id}, "
                f"Project={request.project_full_name} ({request.project_full_path}), "
                f"Status={request.status}, Version={request.port}")

    result = {
        "id": request.id,
        "project_full_path": request.project_full_path,
        "project_full_name": request.project_full_name,
        "status": request.status,
        "port": request.port
    }

    return {
        "success": True,
        "message": "CD callback received",
        "data": result
    }

@router.post("/mcp/run-ci-cd")
def run_ci_cd(request: MCPCICDRequest):
    logger.info(f"run_ci_cd: {request}")

    str_uuid = str(uuid.uuid4())

    async def stream():
        # 1) CI 단계 스트리밍
        status = ""
        yield "data: " + json.dumps({
            "status": "runnging",
            "data": {
                "id": str_uuid,
                "type": "ci",
            },
        }) + "\n\n"


        async for chunk in repo_service.mcp_ci(request.project_full_path, request.project_full_name, str_uuid):
        # async for chunk in repo_service.run_ci(str_uuid):
            logger.info(f"chunk: {chunk}")
            yield chunk

        # 2) CI 성공 시에만 동일 연결에서 CD 진행
            if "success" in chunk:  # 마지막 CI 청크가 success일 때만
                status = "success"
                async for chunk2 in repo_service.run_cd(str_uuid):
                    logger.info(f"chunk2: {chunk2}")
                    yield chunk2
            else:
                status = "failed"

        # 3) 종료 이벤트(선택)
        yield "data: " + json.dumps({
            "status": status,
            "data": {
                "id": str_uuid,
                "type": "cd",
            },
        }) + "\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")