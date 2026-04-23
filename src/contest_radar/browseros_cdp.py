from __future__ import annotations

import base64
import json
import subprocess
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .config_loader import load_runtime_config
from .normalize import canonicalize_url

BROWSEROS_LAUNCHER = "/home/vboxuser/web_clone/scripts/launch-browseros.sh"
BROWSEROS_HEALTH_URL = "http://127.0.0.1:9200/health"
BROWSEROS_CDP_BASE = "http://127.0.0.1:9100"


class BrowserOSUnavailable(RuntimeError):
    pass


def _http_json(url: str, method: str = "GET") -> dict | list:
    request = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _runtime_browseros_config() -> dict:
    payload = load_runtime_config()
    return payload.get("browseros", {}) if isinstance(payload, dict) else {}


def _browseros_endpoint_ready() -> bool:
    try:
        health = _http_json(BROWSEROS_HEALTH_URL)
        if isinstance(health, dict) and health.get("status") == "ok":
            return True
    except Exception:
        pass
    try:
        version = _http_json(f"{BROWSEROS_CDP_BASE}/json/version")
        return isinstance(version, dict) and bool(version.get("webSocketDebuggerUrl") or version.get("Browser"))
    except Exception:
        return False


def ensure_browseros_running(launch_url: str = "https://www.thinkcontest.com/", timeout_seconds: float = 25.0) -> None:
    if _browseros_endpoint_ready():
        return
    subprocess.run(["bash", BROWSEROS_LAUNCHER, launch_url], check=True, timeout=60)
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            if _browseros_endpoint_ready():
                return
        except Exception as exc:  # pragma: no cover - timing dependent
            last_error = exc
        time.sleep(1.0)
    raise BrowserOSUnavailable(f"BrowserOS CDP/health check failed: {last_error}")


@dataclass(slots=True)
class BrowserOSPage:
    page_id: str
    websocket_url: str
    reused: bool = False


def normalize_cdp_url(url: str) -> str:
    return canonicalize_url(url)


def list_pages() -> list[dict]:
    payload = _http_json(f"{BROWSEROS_CDP_BASE}/json/list")
    if not isinstance(payload, list):
        raise BrowserOSUnavailable(f"Unexpected /json/list response: {payload}")
    return payload


def find_reusable_page(url: str, pages: list[dict] | None = None) -> BrowserOSPage | None:
    target_url = normalize_cdp_url(url)
    pages = pages if pages is not None else list_pages()
    for page in pages:
        if page.get("type") != "page":
            continue
        page_url = str(page.get("url") or "")
        if not page_url:
            continue
        if normalize_cdp_url(page_url) != target_url:
            continue
        websocket_url = page.get("webSocketDebuggerUrl")
        page_id = page.get("id")
        if websocket_url and page_id:
            return BrowserOSPage(page_id=str(page_id), websocket_url=str(websocket_url), reused=True)
    return None


class CDPPageSession:
    def __init__(self, page: BrowserOSPage):
        from websocket import WebSocketTimeoutException, create_connection

        self.page = page
        self._timeout_exception = WebSocketTimeoutException
        self._ws = create_connection(page.websocket_url, timeout=90, suppress_origin=True)
        self._ws.settimeout(90)
        self._next_id = 0

    def close(self) -> None:
        close_new_tabs = bool(_runtime_browseros_config().get("close_new_tabs_after_use", True))
        try:
            self._ws.close()
        finally:
            if self.page.reused or not close_new_tabs:
                return
            try:
                urllib.request.urlopen(f"{BROWSEROS_CDP_BASE}/json/close/{self.page.page_id}", timeout=30).read()
            except Exception:
                pass

    def send(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        message_id = self._next_id
        self._ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        while True:
            try:
                payload = json.loads(self._ws.recv())
            except self._timeout_exception as exc:
                raise BrowserOSUnavailable(f"CDP timeout while waiting for {method}") from exc
            if payload.get("id") == message_id:
                if payload.get("error"):
                    raise BrowserOSUnavailable(f"CDP error for {method}: {payload['error']}")
                return payload.get("result", {})

    def evaluate(self, expression: str) -> dict | list | str | int | float | None:
        result = self.send("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        return (result.get("result") or {}).get("value")


def open_page(url: str) -> BrowserOSPage:
    ensure_browseros_running(url)
    browseros_config = _runtime_browseros_config()
    if browseros_config.get("reuse_existing_tabs", True):
        try:
            reused = find_reusable_page(url)
        except BrowserOSUnavailable:
            reused = None
        if reused:
            return reused
    encoded = urllib.parse.quote(url, safe="")
    payload = _http_json(f"{BROWSEROS_CDP_BASE}/json/new?{encoded}", method="PUT")
    if not isinstance(payload, dict) or "id" not in payload or "webSocketDebuggerUrl" not in payload:
        raise BrowserOSUnavailable(f"Unexpected /json/new response: {payload}")
    return BrowserOSPage(page_id=str(payload["id"]), websocket_url=str(payload["webSocketDebuggerUrl"]), reused=False)


def evaluate_url(url: str, expression: str, wait_seconds: float = 3.0) -> dict | list | str | int | float | None:
    page = open_page(url)
    session = CDPPageSession(page)
    try:
        session.send("Page.enable")
        session.send("Runtime.enable")
        session.send("Page.bringToFront")
        session.send("Page.navigate", {"url": url})
        time.sleep(wait_seconds)
        return session.evaluate(expression)
    finally:
        session.close()


def capture_url_screenshot(url: str, output_path: str | Path, wait_seconds: float = 3.0) -> Path:
    page = open_page(url)
    session = CDPPageSession(page)
    path = Path(output_path)
    try:
        session.send("Page.enable")
        session.send("Runtime.enable")
        session.send("Page.bringToFront")
        session.send("Page.navigate", {"url": url})
        time.sleep(wait_seconds)
        result = session.send("Page.captureScreenshot", {"format": "png", "fromSurface": True, "captureBeyondViewport": True})
        image_data = str(result.get("data") or "")
        if not image_data:
            raise BrowserOSUnavailable("CDP screenshot response did not include image data")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(image_data))
        return path
    finally:
        session.close()
