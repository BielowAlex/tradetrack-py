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

from config import load_config, save_last_sync, get_language, debug_log
from config_server import run_bridge_server_forever, run_config_server_until_received
from gui import ask_language_at_startup, create_window
from i18n import get_text
from mt5_sync import connect as mt5_connect, disconnect as mt5_disconnect, get_deals


def get_headers(cfg: dict) -> dict:
    token = (cfg.get("sync_token") or "").strip()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_pending_sync(cfg: dict) -> dict:
    """GET /api/mt5/bridge/pending-sync. Повертає sync_requested, requested_at, last_deal_at, last_deal_ticket."""
    base = (cfg.get("api_base_url") or "").rstrip("/")
    tid = cfg.get("trading_account_id") or ""
    url = f"{base}/api/mt5/bridge/pending-sync"
    try:
        r = requests.get(
            url,
            params={"trading_account_id": tid},
            headers=get_headers(cfg),
            timeout=10,
        )
        if r.status_code != 200:
            return {}
        return r.json()
    except (requests.RequestException, ValueError):
        return {}


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
    print("  • Перевірте логін, пароль і сервер у config.json.")


# MT5: type 0 = BUY, 1 = SELL; entry 0 = IN, 1 = OUT, 2 = INOUT, 3 = OUT_BY. Відправляємо лише закриття (1,2,3).
DEAL_ENTRY_OUT = 1
DEAL_ENTRY_INOUT = 2
DEAL_ENTRY_OUT_BY = 3
DEAL_ENTRY_CLOSING = (DEAL_ENTRY_OUT, DEAL_ENTRY_INOUT, DEAL_ENTRY_OUT_BY)


def _deal_to_item(d: dict) -> dict:
    deal_type = d.get("type", 0)
    direction = "BUY" if deal_type == 0 else "SELL"
    position_id = d.get("position_id")
    if position_id is None or position_id == 0:
        position_id = d.get("ticket", 0)
    try:
        position_id = int(position_id)
    except (TypeError, ValueError):
        position_id = int(d.get("ticket", 0))
    time_val = d.get("time")
    if hasattr(time_val, "timestamp"):
        time_val = int(time_val.timestamp())
    else:
        time_val = int(time_val) if time_val is not None else 0
    return {
        "ticket": d.get("ticket"),
        "positionId": position_id,
        "symbol": str(d.get("symbol", "")).strip(),
        "direction": direction,
        "profit": float(d.get("profit", 0) or 0),
        "volume": float(d.get("volume", 0) or 0),
        "price": float(d.get("price", 0) or 0),
        "time": time_val,
        "commission": float(d.get("commission", 0) or 0),
        "swap": float(d.get("swap", 0) or 0),
        "_position_id": position_id,
        "_time": time_val,
        "_entry": d.get("entry"),
    }


def _to_api_item(item: dict) -> dict:
    return {
        "ticket": item["ticket"],
        "positionId": item["positionId"],
        "symbol": item["symbol"],
        "direction": item["direction"],
        "profit": item["profit"],
        "volume": item["volume"],
        "price": item["price"],
        "time": item["time"],
        "commission": item["commission"],
        "swap": item["swap"],
    }


def _mt5_deals_to_api(mt5_deals: list) -> tuple[list, list]:
    """Повертає (raw_list, deduped_list). deduped — лише закриття (entry OUT/INOUT/OUT_BY), щоб не тягнути відкриті позиції."""
    trade_deals = []
    for d in mt5_deals:
        if d.get("type") not in (0, 1):
            continue
        trade_deals.append(_deal_to_item(d))
    raw_list = [_to_api_item(item) for item in trade_deals]
    # Зразок entry для логів (перші 15 угод)
    entry_sample = [item.get("_entry") for item in trade_deals[:15]]
    debug_log(f"deals: mt5_raw={len(mt5_deals)} type_filtered={len(trade_deals)} entry_sample={entry_sample}")
    by_key: dict = {}
    for item in trade_deals:
        pid = item["_position_id"]
        key = (pid, item["ticket"]) if pid == 0 else pid
        t = item["_time"]
        if key not in by_key or t >= by_key[key]["_time"]:
            by_key[key] = item
    deduped = [
        _to_api_item(item)
        for item in by_key.values()
        if item.get("_entry") in DEAL_ENTRY_CLOSING
    ]
    debug_log(f"deals: after_dedup closing_count={len(deduped)} (entry in 1,2,3)")
    return raw_list, deduped


def _mt5_orders_to_api(mt5_orders: list) -> list:
    """Перетворює історію виконаних ордерів (filled) у формат веб-API. Лише BUY/SELL."""
    result = []
    for o in mt5_orders:
        order_type = o.get("type", 0)
        if order_type not in (0, 1):
            continue
        direction = "BUY" if order_type == 0 else "SELL"
        position_id = o.get("position_id") or o.get("ticket", 0)
        try:
            position_id = int(position_id)
        except (TypeError, ValueError):
            position_id = int(o.get("ticket", 0))
        time_val = o.get("time_done") or o.get("time_setup")
        if hasattr(time_val, "timestamp"):
            time_val = int(time_val.timestamp())
        else:
            time_val = int(time_val) if time_val is not None else 0
        result.append({
            "ticket": o.get("ticket"),
            "positionId": position_id,
            "symbol": str(o.get("symbol", "")).strip(),
            "direction": direction,
            "profit": 0.0,
            "volume": float(o.get("volume_current", 0) or o.get("volume_initial", 0) or 0),
            "price": float(o.get("price_current", 0) or o.get("price_open", 0) or 0),
            "time": time_val,
            "commission": 0.0,
            "swap": 0.0,
        })
    return result


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


def run_sync(cfg: dict, last_sync_at_iso: Optional[str] = None) -> tuple[bool, str, int, list]:
    """Повертає (success, message, synced_count, raw_deals). last_sync_at_iso: якщо задано — тягнемо угоди з початку того дня (включно)."""
    lang = get_language()
    mt5_login = int(cfg.get("mt5_login") or 0)
    mt5_password = cfg.get("mt5_password") or ""
    mt5_server = cfg.get("mt5_server") or ""
    mt5_path = cfg.get("mt5_path") or ""
    tid = (cfg.get("trading_account_id") or "")[:20]
    debug_log(f"run_sync: trading_account_id={tid!r} mt5_login={mt5_login} mt5_server={mt5_server!r}")

    ok, err = mt5_connect(mt5_login, mt5_password, mt5_server, mt5_path=mt5_path or None)
    if not ok:
        debug_log(f"run_sync: MT5 connect failed err={err!r}")
        msg = get_text("msg_mt5_connect_failed", lang).format(err)
        if "-6" in str(err) or "Authorization failed" in str(err):
            msg += get_text("msg_mt5_hint", lang)
        return False, msg, 0, []

    try:
        # Максимально широкий діапазон: ніякої фільтрації по даті — усі угоди за весь час.
        # MT5 API вимагає date_from/date_to, тому передаємо 1970 → зараз+1рік.
        from_time = datetime(1970, 1, 1, tzinfo=pytz.UTC)
        to_time = datetime.now(pytz.UTC) + timedelta(days=365)
        debug_log(f"run_sync: date range from={from_time!s} to={to_time!s}")
        deals = get_deals(from_time, to_time)
        raw_count = len(deals) if deals else 0
        debug_log(f"run_sync: history_deals_get returned {raw_count} deals")
        api_deals_raw, api_deals = _mt5_deals_to_api(deals) if deals else ([], [])

        debug_log(f"run_sync: sending to server api_deals_count={len(api_deals)}")
        if not post_sync_deals(cfg, api_deals):
            debug_log("run_sync: post_sync_deals failed")
            return False, get_text("msg_send_deals_failed", lang), 0, api_deals_raw
        save_last_sync(to_time.isoformat())
        post_bridge_sync_done(cfg)
        if not api_deals:
            debug_log("run_sync: done but 0 closing deals (no new deals)")
            return True, get_text("msg_no_new_deals", lang), 0, api_deals_raw
        debug_log(f"run_sync: success synced={len(api_deals)}")
        return True, get_text("msg_synced_n_deals", lang).format(len(api_deals)), len(api_deals), api_deals_raw
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
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate MT5 credentials from env (MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH) and exit 0/1. Used by bridge in subprocess to avoid terminal stick.",
    )
    args = parser.parse_args()

    if args.validate:
        import os
        try:
            login = int(os.environ.get("MT5_LOGIN", "0"))
        except ValueError:
            print("MT5_LOGIN must be a number", file=sys.stderr)
            sys.exit(1)
        password = os.environ.get("MT5_PASSWORD", "")
        server = (os.environ.get("MT5_SERVER") or "").strip()
        path = (os.environ.get("MT5_PATH") or "").strip() or None
        if not server:
            print("MT5_SERVER required", file=sys.stderr)
            sys.exit(1)
        ok, err = mt5_connect(login, password, server, mt5_path=path)
        if ok:
            mt5_disconnect()
            sys.exit(0)
        if err:
            # Вивід лише ASCII-безпечний текст, щоб у підпроцесі на Windows не було UnicodeEncodeError (cp1252)
            err_safe = (err or "").encode("ascii", errors="replace").decode("ascii")
            print(err_safe, file=sys.stderr)
        sys.exit(1)

    if args.sync_only:
        try:
            cfg = load_config()
        except FileNotFoundError:
            print("No config. Run with GUI and connect from browser first.")
            sys.exit(1)
        ok, msg, _, _ = run_sync(cfg)
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
        input("\nPress Enter to exit...")
    except (EOFError, KeyboardInterrupt):
        pass


def _safe_print(msg: str) -> None:
    """Print without UnicodeEncodeError on Windows (subprocess/cp1252)."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


if __name__ == "__main__":
    is_validate_subprocess = "--validate" in sys.argv
    try:
        used_gui = main()
    except SystemExit as e:
        if e.code and e.code != 0:
            _safe_print(f"\nProgram exited with error (code {e.code}).")
        if not is_validate_subprocess:
            _wait_before_exit()
        raise
    except Exception as e:
        _safe_print(f"\nError: {e}")
        import traceback
        _safe_print(traceback.format_exc())
        if not is_validate_subprocess:
            _wait_before_exit()
        raise
    else:
        if not used_gui and not is_validate_subprocess:
            _wait_before_exit()
