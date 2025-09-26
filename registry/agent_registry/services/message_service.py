import httpx
from pathlib import Path
import json
import logging
import uuid
from typing import Dict, List, Any, Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..core.config import settings
from .server_service import server_service
from datetime import datetime
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import SendStreamingMessageRequest, MessageSendParams

logger = logging.getLogger(__name__)

class ChatEvent(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MessageService:

    async def send_message_to_a2a_agent_stream(self, agent_id: str, message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """A2A 에이전트에게 메시지를 보내고, 그 결과를 스트리밍 방식으로 받아오는 로직"""

        try:
            # Step 1: Agent 정보 조회
            logger.info(f"[Step 1/6] Getting agent details for {agent_id}")
            agent_info = server_service.get_agent_info(agent_id)
            logger.info(f"agent: {agent_info}")
            if not agent_info:
                raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found")

            async with httpx.AsyncClient() as httpx_client:
                logger.info("[Step 1/6] Creating A2A client..."+agent_info["agentCard"]["url"])

                # 1) 카드 조회, 에이전트의 API 접속 정보/메타데이터 가져옴
                resolver = A2ACardResolver(httpx_client=httpx_client, base_url=agent_info["agentCard"]["url"])
                agent_card = await resolver.get_agent_card()  # /.well-known/agent.json
                # 필요 시 확장 카드도 시도 가능: await resolver.get_agent_card(relative_card_path="/agent/authenticatedExtendedCard", http_kwargs={"headers": {...}})

                # 2) 클라이언트 생성
                client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)
                logger.info(f"A2A client ready: {agent_card}")

                # 3) 메시지 준비
                # role: 보낸 쪽의 역할
                # parts: 메시지 본문
                # kind: 메시지 타입
                params = MessageSendParams(
                    message={
                        "messageId": uuid.uuid4().hex,  # 메시지 자체의 ID [web:69]
                        "role": "user",
                        "parts": [{"kind": "text", "text": message}],
                        "kind": "message",
                    }
                )

                # 여기서 요청 자체의 고유 ID를 추가해야 함
                request = SendStreamingMessageRequest(
                    id=uuid.uuid4().hex,
                    params=params,
                )
                logger.info(f"Starting A2A streaming message: {request}")

                # Step 4: 메시지 전송 및 스트리밍, A2A서버로 메시지를 보내고, 서버가 실시간으로 보내주는 이벤트 스트림을 받아옴
                async for event in client.send_message_streaming(request):
                    # event는 JSON 형식
                    # task -> 작업 생성 이벤트
                    # status-update -> 작업 상태 갱신(진행률, 메시지)
                    # artifact-update -> 산출물 업데이트 ex) 생성된 테스트, 파일
                    # 기타 이벤트
                    logger.info(f"Streaming event received: {event}")

                    payload = event.model_dump(mode="json", exclude_none=True)
                    # JSON-RPC 래핑 해제
                    base = payload.get("result") or {}
                    kind = base.get("kind") or base.get("type")  # 여기서는 "task"

                    # 2) kind 추출: SDK/서버에 따라 result 래핑이 있을 수 있음
                    #    - 예시 글에서는 chunk_dict['result'] 아래에 kind/status/artifact가 위치 [web:105]
                    base = payload
                    if "result" in payload and isinstance(payload["result"], dict):
                        base = payload["result"]  # result 아래에 실제 이벤트 필드가 담기는 구현 존재 [web:105][web:69]

                    kind = base.get("kind") or base.get("type")

                    # task 이벤트, kind 기준으로 구분해서,
                    # 호출한 쪽에서 쓰기 쉽게 dict 형태로 가공 후 yield
                    if kind == "task":
                        yield {
                            "type": "task",
                            "data": {
                                "taskId": base.get("taskId") or base.get("id"),
                                "status": (base.get("status") or {}).get("state", "created"),
                                "raw": payload,
                            },
                        }

                    # status-update 이벤트
                    elif kind == "status-update":
                        status_obj = base.get("status") or {}
                        msg = ""
                        parts = (status_obj.get("message") or {}).get("parts") or []
                        for p in parts:
                            if p.get("kind") == "text" and p.get("text"):
                                msg = p["text"];
                                break
                        yield {
                            "type": "status-update",
                            "data": {
                                "taskId": base.get("taskId") or base.get("id"),
                                "message": msg,
                                "progress": base.get("progress"),
                                "final": base.get("final") or False,
                                "raw": payload,
                            },
                        }

                    # artifact-update 이벤트
                    elif kind == "artifact-update":
                        art = base.get("artifact") or {}
                        text = ""
                        for p in art.get("parts", []):
                            if p.get("kind") == "text" and p.get("text"):
                                text = p["text"];
                                break
                        if text:
                            yield {
                                "type": "artifact-update",
                                "data": {
                                    "taskId": base.get("taskId") or base.get("id"),
                                    "name": art.get("name") or art.get("artifactId") or "Generated Content",
                                    "content": text,
                                    "artifactType": art.get("type") or "text",
                                    "raw": payload,
                                },
                            }

                    # 기타 이벤트 패스스루
                    else:
                        yield {"type": kind or "unknown", "data": payload}

                # 완료 이벤트
                yield {"type": "complete", "data": {}}

                logger.info("Message streaming completed.")


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