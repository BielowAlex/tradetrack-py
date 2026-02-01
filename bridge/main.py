"""
TradeTrack MT5 Bridge — клієнт на ПК юзера.
Фронт викликає POST localhost:8765/sync-request при «Get trades» — bridge одразу виконує синк угод з MT5 (без пулінгу).
"""
import sys
from pathlib import Path

# Allow running as python bridge/main.py from repo root
_bridge_dir = Path(__file__).resolve().parent
if str(_bridge_dir) not in sys.path:
    sys.path.insert(0, str(_bridge_dir))

import argparse
import queue
import threading
from datetime import datetime, timedelta
from typing import Optional

import pytz
import requests

from config import load_config, load_last_sync, save_last_sync, get_language
from config_server import run_bridge_server_forever, run_config_server_until_received
from gui import ask_language_at_startup, create_window
from i18n import get_text
from mt5_sync import connect as mt5_connect, disconnect as mt5_disconnect, get_deals


def get_headers(cfg: dict) -> dict:
    token = (cfg.get("sync_token") or "").strip()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def post_bridge_connected(cfg: dict) -> bool:
    base = (cfg.get("api_base_url") or "").rstrip("/")
    tid = cfg.get("trading_account_id") or ""
    url = f"{base}/api/mt5/bridge/connected"
    try:
        r = requests.post(
            url,
            json={"trading_account_id": tid},
            headers=get_headers(cfg),
            timeout=15,
        )
        if r.status_code != 200:
            print(f"Bridge connected failed {r.status_code}: {r.text}")
            return False
        print("Bridge connected: server updated.")
        return True
    except requests.RequestException as e:
        print(f"Bridge connected request error: {e}")
        return False


def _validate_config(cfg: dict) -> None:
    api_base = (cfg.get("api_base_url") or "").strip()
    sync_token = (cfg.get("sync_token") or "").strip()
    trading_account_id = (cfg.get("trading_account_id") or "").strip()
    mt5_password = (cfg.get("mt5_password") or "").strip()
    mt5_server = (cfg.get("mt5_server") or "").strip()
    mt5_login = cfg.get("mt5_login")
    if not api_base or not sync_token or not trading_account_id:
        print("Missing config: api_base_url, sync_token, trading_account_id")
        sys.exit(1)
    if not mt5_password or not mt5_server:
        print("Missing config: mt5_password, mt5_server")
        sys.exit(1)
    try:
        int(mt5_login)
    except (TypeError, ValueError):
        print("mt5_login must be a number")
        sys.exit(1)


def _print_mt5_hint(err: str) -> None:
    if "-6" not in str(err) and "Authorization failed" not in str(err):
        return
    print("\nПідказка (-6 Authorization failed):")
    print("  • Запустіть bridge від того ж користувача, що й MT5.")
    print("  • У MT5: Сервіс → Налаштування → Доп. → дозвольте «Разрешить автоматическую торговлю».")
    print("  • Перевірте логін, інвестор-пароль і сервер у config.json (інвестор-пароль, не основний).")


def post_sync_deals(cfg: dict, deals: list) -> bool:
    base = (cfg.get("api_base_url") or "").rstrip("/")
    tid = cfg.get("trading_account_id") or ""
    url = f"{base}/api/mt5/sync/deals"
    try:
        r = requests.post(
            url,
            json={"trading_account_id": tid, "deals": deals},
            headers=get_headers(cfg),
            timeout=60,
        )
        if r.status_code != 200:
            print(f"Sync deals failed {r.status_code}: {r.text}")
            return False
        return True
    except requests.RequestException as e:
        print(f"Sync deals request error: {e}")
        return False


def post_bridge_sync_done(cfg: dict) -> bool:
    base = (cfg.get("api_base_url") or "").rstrip("/")
    tid = cfg.get("trading_account_id") or ""
    url = f"{base}/api/mt5/bridge/sync-done"
    try:
        r = requests.post(
            url,
            json={"trading_account_id": tid},
            headers=get_headers(cfg),
            timeout=10,
        )
        return r.status_code == 200
    except requests.RequestException:
        return False


def run_sync(cfg: dict) -> tuple[bool, str, int]:
    """Повертає (success, message, synced_count). Повідомлення в поточній мові."""
    lang = get_language()
    mt5_login = int(cfg.get("mt5_login") or 0)
    mt5_password = cfg.get("mt5_password") or ""
    mt5_server = cfg.get("mt5_server") or ""
    mt5_path = cfg.get("mt5_path") or ""

    ok, err = mt5_connect(mt5_login, mt5_password, mt5_server, mt5_path=mt5_path or None)
    if not ok:
        msg = get_text("msg_mt5_connect_failed", lang).format(err)
        if "-6" in str(err) or "Authorization failed" in str(err):
            msg += get_text("msg_mt5_hint", lang)
        return False, msg, 0

    try:
        last = load_last_sync()
        if last:
            from_time = datetime.fromisoformat(last.replace("Z", "+00:00"))
        else:
            from_time = datetime.now(pytz.UTC) - timedelta(days=30)
        to_time = datetime.now(pytz.UTC)
        deals = get_deals(from_time, to_time)

        if not deals:
            save_last_sync(to_time.isoformat())
            post_bridge_sync_done(cfg)
            return True, get_text("msg_no_new_deals", lang), 0

        if not post_sync_deals(cfg, deals):
            return False, get_text("msg_send_deals_failed", lang), 0
        save_last_sync(to_time.isoformat())
        post_bridge_sync_done(cfg)
        return True, get_text("msg_synced_n_deals", lang).format(len(deals)), len(deals)
    finally:
        mt5_disconnect()


def main() -> bool:
    """Повертає True якщо запущено GUI (не питати Enter після виходу)."""
    parser = argparse.ArgumentParser(description="TradeTrack MT5 Bridge")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Connect once, report to server, then exit",
    )
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help="Only run one sync (fetch deals, POST, sync-done) then exit",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Console only: wait for first /config then exit (for initial setup)",
    )
    args = parser.parse_args()

    if args.sync_only:
        try:
            cfg = load_config()
        except FileNotFoundError:
            print("No config. Run with GUI and connect from browser first.")
            sys.exit(1)
        ok, msg, _ = run_sync(cfg)
        if not ok:
            print(msg)
            sys.exit(1)
        return False

    if args.once:
        try:
            cfg = load_config()
        except FileNotFoundError:
            run_config_server_until_received()
            cfg = load_config()
        _validate_config(cfg)
        ok, err = mt5_connect(
            int(cfg["mt5_login"]),
            (cfg.get("mt5_password") or "").strip(),
            (cfg.get("mt5_server") or "").strip(),
            mt5_path=(cfg.get("mt5_path") or "").strip() or None,
        )
        if not ok:
            print(f"MT5 connection failed: {err}")
            _print_mt5_hint(err)
            sys.exit(1)
        post_bridge_connected(cfg)
        mt5_disconnect()
        print("Connected. Exiting.")
        return False

    if args.no_gui:
        try:
            cfg = load_config()
        except FileNotFoundError:
            run_config_server_until_received()
            cfg = load_config()
        print("Config present. Use without --no-gui to run with GUI (no polling).")
        return False

    # GUI mode: спочатку вибір мови, потім локальний сервер і вікно
    ask_language_at_startup()
    msg_queue = queue.Queue()

    def on_config_received() -> None:
        lang = get_language()
        msg_queue.put(("status", get_text("status_connected", lang), False))
        def notify_backend() -> None:
            try:
                cfg = load_config()
                l = get_language()
                if post_bridge_connected(cfg):
                    msg_queue.put(("log", get_text("log_server_notified", l)))
                else:
                    msg_queue.put(("log", get_text("log_server_notify_failed", l)))
            except Exception as e:
                l = get_language()
                msg_queue.put(("log", f"{get_text('log_error', l)} {e}"))
        threading.Thread(target=notify_backend, daemon=True).start()

    server = run_bridge_server_forever(run_sync, on_config_received, msg_queue)

    def on_closing() -> None:
        server.shutdown()

    root, set_status, append_log = create_window(msg_queue, on_closing=on_closing)
    lang = get_language()
    append_log(get_text("log_started", lang))
    append_log(get_text("log_enter_credentials", lang))
    root.mainloop()
    return True  # GUI mode — не питати Enter після закриття


def _wait_before_exit() -> None:
    """Консоль не закривається, поки юзер не натисне Enter (щоб встигнути прочитати помилки)."""
    try:
        input("\nНатисніть Enter для виходу...")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    try:
        used_gui = main()
    except SystemExit as e:
        if e.code and e.code != 0:
            print(f"\nПрограма завершилась з помилкою (код {e.code}).")
        _wait_before_exit()
        raise
    except Exception as e:
        print(f"\nПомилка: {e}")
        import traceback
        traceback.print_exc()
        _wait_before_exit()
        raise
    else:
        if not used_gui:
            _wait_before_exit()
