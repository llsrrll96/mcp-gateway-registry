import httpx
from pathlib import Path
import json
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..core.config import settings
from .server_service import server_service
from datetime import datetime
from a2a.client import A2AClient, A2ACardResolver

logger = logging.getLogger(__name__)

class ChatEvent(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MessageService:

    async def send_message_to_a2a_agent_stream(self, agent_id: str, message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """A2A 메시지 스트리밍 전송"""

        try:
            # Step 1: Agent 정보 조회
            logger.info(f"[Step 1/6] Getting agent details for {agent_id}")
            agent_info = server_service.get_agent_info(agent_id)
            logger.info(f"agent: {agent_info}")
            if not agent_info:
                raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found")

            async with httpx.AsyncClient() as httpx_client:
                logger.info("[Step 1/6] Creating A2A client..."+agent_info["agentCard"]["url"])

                # 1) 카드 조회
                resolver = A2ACardResolver(httpx_client=httpx_client, base_url=agent_info["agentCard"]["url"])
                agent_card = await resolver.get_agent_card()  # /.well-known/agent.json
                # 필요 시 확장 카드도 시도 가능: await resolver.get_agent_card(relative_card_path="/agent/authenticatedExtendedCard", http_kwargs={"headers": {...}})

                # 2) 클라이언트 생성
                client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)
                print("A2A client ready:", agent_card.name, agent_card.version)

                # 3) 메시지 준비
            logger.info(f"A2A client created successfully: {client}")

        except Exception as error:
            logger.error(f"Error in A2A streaming: {str(error)}")
            yield ChatEvent(
                type="error",
                data={
                    "message": str(error) if isinstance(error, Exception) else "Unknown error occurred"
                }
            )
# Global service instance
message_service = MessageService()