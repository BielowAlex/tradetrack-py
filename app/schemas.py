from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Mt5ConnectRequest(BaseModel):
    trading_account_id: int
    mt5_login: int
    mt5_server: str
    investor_password: str


class Mt5ConnectResponse(BaseModel):
    success: bool
    account_id: Optional[int] = None
    status: str
    message: Optional[str] = None


class Mt5TestConnectionRequest(BaseModel):
    mt5_login: int
    mt5_server: str
    investor_password: str


class Mt5TestConnectionResponse(BaseModel):
    success: bool
    message: str
    account_info: Optional[dict] = None


class Mt5StatusResponse(BaseModel):
    trading_account_id: int
    status: str
    mt5_login: Optional[int] = None
    mt5_server: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    error_message: Optional[str] = None


class Mt5SyncResponse(BaseModel):
    success: bool
    synced: int = 0
    skipped: int = 0
    errors: list = []
    total: int = 0
    message: Optional[str] = None


class DisconnectResponse(BaseModel):
    success: bool
    message: str
