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


# from ..core.config import settings
# from ..auth.dependencies import web_auth, api_auth, enhanced_auth
# from ..services.server_service import server_service

from ..services.server_service import server_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/mcp", name="servers")
async def get_servers_json():
    all_servers = server_service.get_all_servers()


    from registry.health.service import health_service


@router.post("/mcp", name="mcp_register")
async def mcp_register_service(
    name: Annotated[str, Form()],
    version: Annotated[str, Form()] = "1.0",
    description: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
    type: Annotated[str, Form()] = "analysis",
    scope: Annotated[str, Form()] = "external",
    migrationStatus: Annotated[str, Form()] = "none",
    serverUrl: Annotated[str, Form()] = "",
    protocol: Annotated[str, Form()] = "http",
    security: Annotated[str, Form()] = "{}",
    supportedFormats: Annotated[str, Form()] = "[]",  # JSON 문자열 형태로 받음
    tags: Annotated[str, Form()] = "[]",             # JSON 문자열 형태로 받음
    environment: Annotated[str, Form()] = "production",

):
    from ..search.service import faiss_service

    logger.info(f"***Name: {name}, URL: {serverUrl}")

    # 1. 최종 path 생성
    path = uuid.uuid4()


    # 기존 저장
    from registry.api.server_routes import register_service
        # form 데이터 준비
    # register_service 호출 (HTTP 호출이 아니라 내부 함수 호출)
    await register_service(
        name=name,
        description=description,
        path=path,
        proxy_pass_url=serverUrl,
        tags=tags,
        num_tools=0,
        num_stars=0,
        is_python=False,
        license_str="N/A",
        user_context= None,
    )

    # Process tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    id = uuid.uuid4()

    # Create server entry
    server_entry = {
        "id": id,
        "name": name,
        "version": version,
        "description": description,
        "status": status,
        "type": type,
        "scope": scope,
        "migrationStatus": migrationStatus,
        "serverUrl": serverUrl,
        "protocol": protocol,
        "security": security,
        "supportedFormats": supportedFormats,
        "tags": tag_list,
        "environment": environment,
        "tool_list": [],
        "path": path
    }

    # Register the server
    success = server_service.register_server(server_entry)

    if not success:
        return JSONResponse(
            status_code=400,
            content={"error": f"Service failed to save"},
        )

    # Add to FAISS index (disabled by default) -- X

    # Regenerate Nginx configuration

    # Broadcast health status update to WebSocket clients

    # enable true 가  default 인 과정

    return JSONResponse(
        status_code=201,
        content={
            "message": "Service registered successfully",
            "service": server_entry,
        },
    )