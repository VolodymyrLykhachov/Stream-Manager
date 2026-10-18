"""Home Assistant REST and websocket client for states and camera streams."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable

import aiohttp

log = logging.getLogger("onvif_proxy.ha")


class HaError(Exception):
    pass


@dataclass
class Playback:
    mode: str | None
    error: str | None
    upstream: str = ""


class HaClient:
    def __init__(self, ha_url: str, token: str, supervisor: bool, poll_seconds: int) -> None:
        self.ha_url = ha_url.rstrip("/")
        self.token = token
        self.supervisor = supervisor
        self.poll_seconds = poll_seconds
        self.connected = False
        self.ws_connected = False
        self.error = ""
        self.mode = "supervisor" if supervisor else ("local" if token and ha_url else "off")
        self.states: dict[str, str] = {}
        self.entities: dict[str, dict] = {}
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._seq = 0
        self._stop = asyncio.Event()
        self._send_lock = asyncio.Lock()
        self._hls: dict[str, tuple[float, str]] = {}
        self._auth_mode = "access_token"
        self.on_change: Callable[[], None] | None = None

    def origin(self) -> str:
        if self.supervisor:
            return "http://supervisor/core"
        return self.ha_url

    def api_url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return self.origin() + path

    def ws_url(self) -> str:
        if self.supervisor:
            return "ws://supervisor/core/websocket"
        base = self.ha_url
        if base.startswith("https://"):
            return "wss://" + base[len("https://") :] + "/api/websocket"
        if base.startswith("http://"):
            return "ws://" + base[len("http://") :] + "/api/websocket"
        return base

    def auth_headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    async def start(self) -> None:
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        if not self.token or not self.origin():
            self.connected = False
            self.error = "Home Assistant is not connected"
            return
        asyncio.create_task(self._poll_loop())
        asyncio.create_task(self._ws_loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._ws is not None:
            await self._ws.close()
        if self._session is not None:
            await self._session.close()

    def schedule_change(self) -> None:
        if self.on_change:
            self.on_change()

    async def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self.refresh_states()
                self.connected = True
                if not self.ws_connected:
                    self.error = ""
                self.schedule_change()
            except Exception as exc:
                if not self.ws_connected:
                    self.connected = False
                    self.error = str(exc)
                log.debug("state poll failed: %s", exc)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.poll_seconds)
            except asyncio.TimeoutError:
                continue

    async def refresh_states(self) -> None:
        if self._session is None:
            raise HaError("HTTP session is not started")
        async with self._session.get(self.api_url("/api/states"), headers=self.auth_headers()) as response:
            if response.status != 200:
                text = await response.text()
                raise HaError(f"Home Assistant states HTTP {response.status}: {text[:180]}")
            payload = await response.json()
        self._replace_states(payload)

    def _replace_states(self, payload: list[dict]) -> None:
        states: dict[str, str] = {}
        entities: dict[str, dict] = {}
        for item in payload:
            entity_id = str(item.get("entity_id") or "")
            if not entity_id:
                continue
            attributes = item.get("attributes") or {}
            states[entity_id] = str(item.get("state") or "")
            entities[entity_id] = {
                "entity_id": entity_id,
                "state": states[entity_id],
                "friendly_name": str(attributes.get("friendly_name") or entity_id),
                "domain": entity_id.split(".", 1)[0],
            }
        self.states = states
        self.entities = entities

    async def _ws_loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self._ws_once()
            except Exception as exc:
                self.ws_connected = False
                if not self.connected:
                    self.error = str(exc)
                log.info("websocket disconnected: %s", exc)
            if self._stop.is_set():
                return
            await asyncio.sleep(5)

    async def _ws_once(self) -> None:
        assert self._session is not None
        async with self._session.ws_connect(self.ws_url(), heartbeat=30) as ws:
            self._ws = ws
            first = await ws.receive_json()
            if first.get("type") != "auth_required":
                raise HaError("unexpected websocket greeting")
            if self._auth_mode == "api_password":
                await ws.send_json({"type": "auth", "api_password": self.token})
            else:
                await ws.send_json({"type": "auth", "access_token": self.token})
            auth = await ws.receive_json()
            if auth.get("type") != "auth_ok":
                self._auth_mode = "api_password" if self._auth_mode == "access_token" else "access_token"
                raise HaError("Home Assistant websocket rejected the token")
            self.ws_connected = True
            self.connected = True
            self.error = ""
            log.info("connected to Home Assistant websocket")
            reader = asyncio.create_task(self._read_loop(ws))
            try:
                await self.ws_command({"type": "subscribe_events", "event_type": "state_changed"})
                listed = await self.ws_command({"type": "get_states"})
                if isinstance(listed, list):
                    self._replace_states(listed)
                    self.schedule_change()
                await reader
            finally:
                self.ws_connected = False
                self._ws = None
                reader.cancel()

    async def _read_loop(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        async for message in ws:
            if message.type != aiohttp.WSMsgType.TEXT:
                continue
            data = message.json()
            if data.get("type") == "result":
                future = self._pending.pop(int(data.get("id") or 0), None)
                if future and not future.done():
                    if data.get("success"):
                        future.set_result(data.get("result"))
                    else:
                        err = data.get("error") or {}
                        future.set_exception(HaError(str(err.get("message") or err)))
                continue
            if data.get("type") == "event":
                event = data.get("event") or {}
                if event.get("event_type") != "state_changed":
                    continue
                body = event.get("data") or {}
                entity_id = str(body.get("entity_id") or "")
                new_state = body.get("new_state")
                if not entity_id:
                    continue
                if new_state is None:
                    self.states.pop(entity_id, None)
                    self.entities.pop(entity_id, None)
                else:
                    self.states[entity_id] = str(new_state.get("state") or "")
                    attributes = new_state.get("attributes") or {}
                    self.entities[entity_id] = {
                        "entity_id": entity_id,
                        "state": self.states[entity_id],
                        "friendly_name": str(attributes.get("friendly_name") or entity_id),
                        "domain": entity_id.split(".", 1)[0],
                    }
                self.schedule_change()

    async def ws_command(self, payload: dict) -> Any:
        if self._ws is None:
            raise HaError("Home Assistant websocket is not connected")
        loop = asyncio.get_running_loop()
        self._seq += 1
        message_id = self._seq
        future: asyncio.Future = loop.create_future()
        self._pending[message_id] = future
        async with self._send_lock:
            await self._ws.send_json({**payload, "id": message_id})
        return await asyncio.wait_for(future, timeout=20)

    async def camera_stream_url(self, entity_id: str) -> str:
        result = await self.ws_command({"type": "camera/stream", "entity_id": entity_id, "format": "hls"})
        if not isinstance(result, dict) or not result.get("url"):
            raise HaError("camera/stream did not return a URL")
        url = str(result["url"])
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return self.origin() + url

    async def ensure_hls(self, entity_id: str) -> str:
        import time

        cached = self._hls.get(entity_id)
        now = time.time()
        if cached and now - cached[0] < 45:
            return cached[1]
        url = await self.camera_stream_url(entity_id)
        self._hls[entity_id] = (now, url)
        return url

    async def playback_for_entity(self, entity_id: str) -> Playback:
        if not self.token or not self.origin():
            return Playback(None, "Home Assistant is not connected")
        if not self.connected and not self.ws_connected:
            return Playback(None, self.error or "Home Assistant is not connected")
        if self.states and entity_id not in self.states:
            return Playback(None, f"{entity_id} is not in Home Assistant")
        try:
            upstream = await self.ensure_hls(entity_id)
            return Playback("hls", None, upstream)
        except Exception as exc:
            log.info("camera/stream failed for %s: %s", entity_id, exc)
            if not self.connected:
                return Playback(None, "Home Assistant is not connected")
            log.warning("using MJPEG fallback for camera %s after camera/stream failed", entity_id)
            return Playback("mjpeg", None, self.api_url(f"/api/camera_proxy_stream/{entity_id}"))

    def inject_states(self, updates: dict[str, str]) -> None:
        for entity_id, state in updates.items():
            self.states[str(entity_id)] = str(state)
            self.entities.setdefault(
                str(entity_id),
                {
                    "entity_id": str(entity_id),
                    "state": str(state),
                    "friendly_name": str(entity_id),
                    "domain": str(entity_id).split(".", 1)[0],
                },
            )
            self.entities[str(entity_id)]["state"] = str(state)
        self.schedule_change()

    def allowed_upstream(self, url: str) -> bool:
        return url.startswith(self.origin() + "/") or url == self.origin()
