import json
import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import httpx
from urllib.parse import urlparse
import uuid
from pydantic import BaseModel
from typing import List, Dict, Optional

# from ..core.config import settings
from ...auth.dependencies import web_auth, api_auth, enhanced_auth
from ..services.server_service import server_service

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
    security: Optional[Dict] = {}
    supportedFormats: Optional[List[str]] = []
    tags: Optional[List[str]] = []
    environment: Optional[str] = "production"


@router.get("/mcp", name="servers")
async def get_servers_json():
    logger.info(f"get_servers_json")
    all_servers = server_service.get_all_servers()


    return {"data" : all_servers}


@router.post("/mcp", name="mcp_register")
async def mcp_register_service(
        body: MCPRegisterRequest,
        user_context: dict = Depends(enhanced_auth)
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
    response: JSONResponse = await register_service(
        name=body.name,
        description=body.description,
        path=path,
        proxy_pass_url=body.serverUrl,
        tags=tag_str,
        num_tools=0,
        num_stars=0,
        is_python=False,
        license_str="N/A",
        user_context= user_context
    )
    if response.status_code != 201:
        try:
            body_json = json.loads(response.body.decode())
            message_content = body_json.get("error") if isinstance(body_json, dict) else str(body_json)
        except Exception:
            message_content = "failed to regist server"
        return JSONResponse(
            status_code=response.status_code,
            content={
                "success": False,
                "message": message_content
            }
        )

    id = str(raw_uuid)

    # Create server entry
    server_entry = {
        "id": id,
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
        "tool_list": [],
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
    from registry.api.server_routes import toggle_service_route
    response: JSONResponse = await toggle_service_route(
        request=None,
        service_path=path,
        enabled="on",  # Form 데이터 대체
        user_context=user_context,
    )
    if response.status_code == 200:
        logger.info(f"enable 성공: {response.body.decode()}")
        # tool_list 를 가져와서 , servers json 에 채우기
        # MCP 서버에서 최신 tool 목록 가져오기

        # 기존 서버 정보와 비교

        # 변경된 경우 서버 정보 갱신

    else:
        logger.error(f"enable 실패: '{response.status_code}', off 로 설정", )

    return JSONResponse(
        status_code=201,
        content={
            "success": True,
            "data": server_entry
        },
    )