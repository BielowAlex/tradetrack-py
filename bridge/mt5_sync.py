from datetime import datetime
from typing import List, Dict, Tuple, Optional
import pytz

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

MT5_TIMEOUT_MS = 30000


def connect(
    mt5_login: int,
    mt5_password: str,
    mt5_server: str,
    mt5_path: Optional[str] = None,
    timeout: int = MT5_TIMEOUT_MS,
) -> Tuple[bool, Optional[str]]:
    if not MT5_AVAILABLE:
        return False, "MetaTrader5 is not installed (Windows only)."
    # Закрити попереднє з'єднання, щоб термінал не лишався на "останньому" (невдалому) рахунку
    mt5.shutdown()
    # Передаємо логін/пароль/сервер одразу в initialize(), щоб підключити потрібний рахунок,
    # а не "останній у терміналі" (який може бути в стані помилки авторизації)
    init_kwargs: dict = {
        "login": mt5_login,
        "password": mt5_password,
        "server": mt5_server.strip(),
        "timeout": timeout,
    }
    if mt5_path and str(mt5_path).strip():
        path_str = str(mt5_path).strip()
        ok = mt5.initialize(path_str, **init_kwargs)
    else:
        ok = mt5.initialize(**init_kwargs)
    if not ok:
        err = f"MT5 init failed: {mt5.last_error()}"
        mt5.shutdown()
        return False, err
    info = mt5.account_info()
    if info is not None and getattr(info, "login", None) == mt5_login:
        return True, None
    # Якщо initialize() пройшов, але рахунок інший — пробуємо login()
    if not mt5.login(mt5_login, password=mt5_password, server=mt5_server):
        err = f"MT5 login failed: {mt5.last_error()}"
        mt5.shutdown()
        return False, err
    return True, None


def disconnect() -> None:
    if MT5_AVAILABLE and mt5:
        mt5.shutdown()


def get_deals(from_time: datetime, to_time: datetime) -> List[Dict]:
    if not MT5_AVAILABLE or mt5 is None:
        return []
    tz = pytz.UTC
    from_t = from_time if from_time.tzinfo else tz.localize(from_time)
    to_t = to_time if to_time.tzinfo else tz.localize(to_time)
    # datetime в UTC; group не передаємо — усі символи. (timestamp іноді давав обмежений результат.)
    deals = mt5.history_deals_get(from_t, to_t)
    if deals is None:
        try:
            from config import debug_log
            err = mt5.last_error()
            debug_log(f"history_deals_get returned None; mt5.last_error()={err}")
        except Exception:
            pass
        return []
    return [d._asdict() for d in deals]


ORDER_STATE_FILLED = 4


def get_history_orders(from_time: datetime, to_time: datetime) -> List[Dict]:
    if not MT5_AVAILABLE or mt5 is None:
        return []
    tz = pytz.UTC
    from_t = from_time if from_time.tzinfo else tz.localize(from_time)
    to_t = to_time if to_time.tzinfo else tz.localize(to_time)
    orders = mt5.history_orders_get(from_t, to_t)
    if orders is None:
        return []
    result = []
    for o in orders:
        if getattr(o, "state", None) != ORDER_STATE_FILLED:
            continue
        result.append(o._asdict())
    return result
