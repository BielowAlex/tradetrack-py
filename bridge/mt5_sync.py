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
    init_kwargs: dict = {"timeout": timeout}
    if mt5_path and str(mt5_path).strip():
        init_kwargs["path"] = str(mt5_path).strip()
    if not mt5.initialize(**init_kwargs):
        return False, f"MT5 init failed: {mt5.last_error()}"
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
    deals = mt5.history_deals_get(from_t, to_t)
    if deals is None:
        return []
    return [d._asdict() for d in deals]
