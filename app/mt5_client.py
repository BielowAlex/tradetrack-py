from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from app.config import settings
import pytz

# MetaTrader5 доступна тільки на Windows
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None


class MT5Client:
    def __init__(self):
        self.connected = False
        self.login = None
        self.server = None
        
        if not MT5_AVAILABLE:
            raise RuntimeError(
                "MetaTrader5 library is not available. "
                "It can only be installed on Windows. "
                "For Linux, please use a Windows machine or Windows server for MT5 integration."
            )

    def connect(self, login: int, password: str, server: str) -> Tuple[bool, Optional[str]]:
        if not MT5_AVAILABLE:
            return False, "MetaTrader5 library is not available on this platform"
            
        if not mt5.initialize(path=settings.mt5_path, timeout=settings.mt5_timeout):
            error = f"MT5 initialization failed: {mt5.last_error()}"
            return False, error

        authorized = mt5.login(login, password=password, server=server)
        if not authorized:
            error = f"MT5 login failed: {mt5.last_error()}"
            mt5.shutdown()
            return False, error

        self.connected = True
        self.login = login
        self.server = server
        return True, None

    def disconnect(self):
        if not MT5_AVAILABLE:
            return
            
        if self.connected:
            mt5.shutdown()
            self.connected = False
            self.login = None
            self.server = None

    def get_account_info(self) -> Optional[Dict]:
        if not MT5_AVAILABLE or not self.connected:
            return None
        account_info = mt5.account_info()
        if account_info is None:
            return None
        return account_info._asdict()

    def get_deals(self, from_time: datetime, to_time: datetime) -> List[Dict]:
        if not MT5_AVAILABLE or not self.connected:
            return []

        timezone = pytz.UTC
        from_time_tz = timezone.localize(from_time) if from_time.tzinfo is None else from_time
        to_time_tz = timezone.localize(to_time) if to_time.tzinfo is None else to_time

        deals = mt5.history_deals_get(from_time_tz, to_time_tz)
        if deals is None:
            return []

        result = []
        for deal in deals:
            deal_dict = deal._asdict()
            result.append(deal_dict)

        return result

    def is_connected(self) -> bool:
        if not MT5_AVAILABLE:
            return False
        return self.connected and mt5.terminal_info() is not None
