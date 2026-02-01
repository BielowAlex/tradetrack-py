"""
Локальний сервер: POST /config від фронту, GET/POST /sync-request для синку без пулінгу.
Сервер працює постійно; після /config не завершується — очікує /sync-request з браузера.
"""
import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional

from config import load_config, save_config, get_language
from i18n import get_text

CONFIG_SERVER_HOST = "127.0.0.1"
CONFIG_SERVER_PORT = 8765

REQUIRED_KEYS = ("api_base_url", "sync_token", "trading_account_id", "mt5_login", "mt5_password", "mt5_server")


def _send_cors_headers(handler: BaseHTTPRequestHandler) -> None:
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Max-Age", "86400")


class BridgeHandler(BaseHTTPRequestHandler):
    """Обробник: /config, /sync-request; не завершує сервер після /config."""
    on_config_received: Optional[Callable[[], None]] = None
    sync_runner: Optional[Callable[[dict], tuple[bool, str, int]]] = None  # (success, message, synced_count)
    msg_queue: Optional[queue.Queue] = None  # (log|status, msg[, is_error])

    def log_message(self, format: str, *args: object) -> None:
        pass

    def _log(self, msg: str) -> None:
        if self.msg_queue is not None:
            self.msg_queue.put(("log", msg))

    def _status(self, msg: str, is_error: bool = False) -> None:
        if self.msg_queue is not None:
            self.msg_queue.put(("status", msg, is_error))

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        _send_cors_headers(self)
        self.end_headers()

    def do_GET(self) -> None:
        if self.path in ("/", "/status"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            _send_cors_headers(self)
            self.end_headers()
            try:
                load_config()
                connected = True
            except FileNotFoundError:
                connected = False
            lang = get_language()
            body = {
                "app": "TradeTrack Sync",
                "description": get_text("api_description", lang),
                "endpoints": {
                    "config": get_text("api_config_endpoint", lang),
                    "sync": get_text("api_sync_endpoint", lang),
                },
                "connected": connected,
                "status": get_text("api_status_connected", lang) if connected else get_text("api_status_not_connected", lang),
            }
            self.wfile.write(json.dumps(body, ensure_ascii=False).encode("utf-8"))
        elif self.path.startswith("/sync-request"):
            self._handle_sync_request()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/config":
            self._handle_config()
        elif self.path.startswith("/sync-request"):
            self._handle_sync_request()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_config(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._send_json(400, {"error": "Empty body"})
            return
        try:
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self._send_json(400, {"error": str(e)})
            return
        missing = [k for k in REQUIRED_KEYS if not data.get(k)]
        if missing:
            self._send_json(400, {"error": f"Missing: {', '.join(missing)}"})
            return
        try:
            login = data["mt5_login"]
            int(login)
        except (TypeError, ValueError):
            self._send_json(400, {"error": "mt5_login must be a number"})
            return
        config = {
            "api_base_url": str(data["api_base_url"]).strip().rstrip("/"),
            "sync_token": str(data["sync_token"]).strip(),
            "trading_account_id": str(data["trading_account_id"]).strip(),
            "mt5_login": int(login),
            "mt5_password": str(data["mt5_password"]),
            "mt5_server": str(data["mt5_server"]).strip(),
            "mt5_path": str(data.get("mt5_path") or "").strip(),
        }
        save_config(config)
        self._send_json(200, {"ok": True, "message": "Config saved. Connecting..."})
        lang = get_language()
        self._log(get_text("log_config_from_browser", lang))
        self._log(get_text("log_config_saved", lang))
        if BridgeHandler.on_config_received:
            BridgeHandler.on_config_received()

    def _handle_sync_request(self) -> None:
        if BridgeHandler.sync_runner is None:
            self._send_json(500, {"error": "Sync runner not set"})
            return
        try:
            cfg = load_config()
        except FileNotFoundError:
            self._send_json(400, {"error": "No config. Connect from browser first."})
            return
        lang = get_language()
        self._status(get_text("status_syncing", lang))
        self._log(get_text("log_sync_requested", lang))
        self._log(get_text("status_syncing", lang))
        success, message, synced = BridgeHandler.sync_runner(cfg)
        if success:
            self._send_json(200, {"ok": True, "message": message, "synced": synced})
            self._status(get_text("status_connected", lang))
            if synced:
                self._log(get_text("log_deals_sent", lang))
            else:
                self._log(f"{get_text('log_sync_done', lang)} {message}")
        else:
            self._send_json(500, {"ok": False, "error": message})
            self._status(get_text("status_mt5_error", lang), is_error=True)
            self._log(f"{get_text('log_error', lang)} {message}")

    def _send_json(self, code: int, obj: dict) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        _send_cors_headers(self)
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode("utf-8"))


def run_bridge_server_forever(
    sync_runner: Callable[[dict], tuple[bool, str, int]],
    on_config_received: Callable[[], None],
    msg_queue: queue.Queue,
):
    """Запустити сервер на 8765 у фоні; повертає server для shutdown при закритті вікна."""
    BridgeHandler.sync_runner = sync_runner
    BridgeHandler.on_config_received = on_config_received
    BridgeHandler.msg_queue = msg_queue
    server = HTTPServer((CONFIG_SERVER_HOST, CONFIG_SERVER_PORT), BridgeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def run_config_server_until_received() -> None:
    """Режим консолі (без GUI): сервер до першого POST /config, потім завершення."""
    received = threading.Event()
    BridgeHandler.on_config_received = lambda: received.set()
    BridgeHandler.sync_runner = None
    BridgeHandler.msg_queue = None
    server = HTTPServer((CONFIG_SERVER_HOST, CONFIG_SERVER_PORT), BridgeHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"Bridge: waiting for connection from browser.")
    print(f"  Open your web app → bridge section → click Connect.")
    print(f"  (Frontend must POST config to http://{CONFIG_SERVER_HOST}:{CONFIG_SERVER_PORT}/config)")
    print()
    received.wait()
    server.shutdown()
    print("Config received from browser. Connecting to MT5...")
