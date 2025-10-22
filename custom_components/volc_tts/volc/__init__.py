#!/usr/bin/env python3
import asyncio
import copy
import json
import logging
import uuid
from collections.abc import AsyncGenerator

import websockets

from .protocols import (
    EventType,
    MsgType,
    finish_connection,
    finish_session,
    receive_message,
    start_connection,
    start_session,
    task_request,
    wait_for_event,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_resource_id(voice: str) -> str:
    if voice.startswith("S_"):
        return "volc.megatts.default"
    return "volc.service_type.10029"


class VolcTTSClient:
    def __init__(
        self, *, appid, access_token, voice_type="zh_female_wanwanxiaohe_moon_bigtts"
    ):
        self.websocket = None
        self.appid = appid
        self.access_token = access_token
        self.voice_type = voice_type
        self.connected = False

    async def connect(self):
        headers = {
            "X-Api-App-Key": self.appid,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": get_resource_id(self.voice_type),
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }

        websocket = await websockets.connect(
            "wss://openspeech.bytedance.com/api/v3/tts/bidirection",
            additional_headers=headers,
            max_size=10 * 1024 * 1024,
        )

        await start_connection(websocket)
        await wait_for_event(
            websocket, MsgType.FullServerResponse, EventType.ConnectionStarted
        )
        self.websocket = websocket
        self.connected = True

    async def disconnect(self):
        if self.websocket is None:
            return
        await finish_connection(self.websocket)
        await wait_for_event(
            self.websocket, MsgType.FullServerResponse, EventType.ConnectionFinished
        )
        await self.websocket.close()
        self.websocket = None
        self.connected = False

    async def tts(self, chunk_stream: AsyncGenerator[str]):
        if not self.connected:
            await self.connect()
        base_request = {
            "user": {
                "uid": str(uuid.uuid4()),
            },
            "namespace": "BidirectionalTTS",
            "req_params": {
                "speaker": self.voice_type,
                "audio_params": {
                    "format": "mp3",
                    "sample_rate": 24000,
                    "enable_timestamp": True,
                },
                "additions": json.dumps(
                    {
                        "disable_markdown_filter": False,
                    }
                ),
            },
        }
        start_session_request = copy.deepcopy(base_request)
        start_session_request["event"] = EventType.StartSession
        session_id = str(uuid.uuid4())

        await start_session(
            self.websocket, json.dumps(start_session_request).encode(), session_id
        )
        await wait_for_event(
            self.websocket, MsgType.FullServerResponse, EventType.SessionStarted
        )

        async def _sender():
            async for chunk in chunk_stream:
                synthesis_request = copy.deepcopy(base_request)
                synthesis_request["event"] = EventType.TaskRequest
                synthesis_request["req_params"]["text"] = chunk

                await task_request(
                    self.websocket, json.dumps(synthesis_request).encode(), session_id
                )
            await finish_session(self.websocket, session_id)

        sender_task = asyncio.create_task(_sender())

        try:
            while True:
                msg = await receive_message(self.websocket)

                if msg.type == MsgType.FullServerResponse:
                    if msg.event == EventType.SessionFinished:
                        break
                elif msg.type == MsgType.AudioOnlyServer:
                    if len(msg.payload) > 0:
                        yield msg.payload
                else:
                    raise RuntimeError(f"TTS conversion failed: {msg}")
        finally:
            sender_task.cancel()
            await asyncio.gather(sender_task, return_exceptions=True)
