from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional
import pytz

from app.database import get_db
from app.auth import verify_token, get_user_id_from_token
from app.encryption import encryption_service
from app.mt5_client import MT5Client
from app.schemas import (
    Mt5ConnectRequest,
    Mt5ConnectResponse,
    Mt5TestConnectionRequest,
    Mt5TestConnectionResponse,
    Mt5StatusResponse,
    Mt5SyncResponse,
    DisconnectResponse
)
from app.models import Mt5InvestorAccount

router = APIRouter(prefix="/api/mt5", tags=["MT5"])


def get_authorization_token(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    return authorization.replace("Bearer ", "")


def verify_trading_account_access(
    trading_account_id: int,
    user_id: int,
    db: Session
) -> bool:
    query = text("""
        SELECT ta.id, ta.user_id
        FROM trading_accounts ta
        WHERE ta.id = :account_id
    """)
    result = db.execute(query, {"account_id": trading_account_id}).fetchone()
    
    if not result:
        return False
    
    account_user_id = result[1]
    return account_user_id == user_id


@router.post("/connect", response_model=Mt5ConnectResponse)
async def connect_mt5(
    request: Mt5ConnectRequest,
    token: str = Depends(get_authorization_token),
    db: Session = Depends(get_db)
):
    payload = verify_token(token)
    user_id = get_user_id_from_token(token)
    
    if not verify_trading_account_access(request.trading_account_id, user_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this trading account"
        )

    mt5_client = MT5Client()
    success, error = mt5_client.connect(
        request.mt5_login,
        request.investor_password,
        request.mt5_server
    )

    if not success:
        mt5_client.disconnect()
        return Mt5ConnectResponse(
            success=False,
            status="ERROR",
            message=error
        )

    account_info = mt5_client.get_account_info()
    mt5_client.disconnect()

    encrypted_password = encryption_service.encrypt(request.investor_password)

    existing_account = db.query(Mt5InvestorAccount).filter(
        Mt5InvestorAccount.trading_account_id == request.trading_account_id
    ).first()

    if existing_account:
        existing_account.mt5_login = request.mt5_login
        existing_account.mt5_server = request.mt5_server
        existing_account.encrypted_investor_password = encrypted_password
        existing_account.status = "CONNECTED"
        existing_account.error_message = None
        account_id = existing_account.id
    else:
        new_account = Mt5InvestorAccount(
            trading_account_id=request.trading_account_id,
            mt5_login=request.mt5_login,
            mt5_server=request.mt5_server,
            encrypted_investor_password=encrypted_password,
            status="CONNECTED"
        )
        db.add(new_account)
        db.commit()
        db.refresh(new_account)
        account_id = new_account.id

    return Mt5ConnectResponse(
        success=True,
        account_id=account_id,
        status="CONNECTED",
        message="Successfully connected to MT5"
    )


@router.post("/test-connection", response_model=Mt5TestConnectionResponse)
async def test_connection(
    request: Mt5TestConnectionRequest,
    token: str = Depends(get_authorization_token),
    db: Session = Depends(get_db)
):
    verify_token(token)

    mt5_client = MT5Client()
    success, error = mt5_client.connect(
        request.mt5_login,
        request.investor_password,
        request.mt5_server
    )

    if not success:
        mt5_client.disconnect()
        return Mt5TestConnectionResponse(
            success=False,
            message=error
        )

    account_info = mt5_client.get_account_info()
    mt5_client.disconnect()

    if account_info:
        return Mt5TestConnectionResponse(
            success=True,
            message="Connection successful",
            account_info={
                "login": account_info.get("login"),
                "server": account_info.get("server"),
                "balance": account_info.get("balance"),
                "equity": account_info.get("equity"),
            }
        )

    return Mt5TestConnectionResponse(
        success=True,
        message="Connection successful, but could not retrieve account info"
    )


@router.get("/status/{trading_account_id}", response_model=Mt5StatusResponse)
async def get_status(
    trading_account_id: int,
    token: str = Depends(get_authorization_token),
    db: Session = Depends(get_db)
):
    payload = verify_token(token)
    user_id = get_user_id_from_token(token)

    if not verify_trading_account_access(trading_account_id, user_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this trading account"
        )

    account = db.query(Mt5InvestorAccount).filter(
        Mt5InvestorAccount.trading_account_id == trading_account_id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MT5 account not found"
        )

    return Mt5StatusResponse(
        trading_account_id=trading_account_id,
        status=account.status,
        mt5_login=account.mt5_login,
        mt5_server=account.mt5_server,
        last_sync_at=account.last_sync_at,
        error_message=account.error_message
    )


@router.post("/sync/{trading_account_id}", response_model=Mt5SyncResponse)
async def sync_trades(
    trading_account_id: int,
    token: str = Depends(get_authorization_token),
    db: Session = Depends(get_db)
):
    payload = verify_token(token)
    user_id = get_user_id_from_token(token)

    if not verify_trading_account_access(trading_account_id, user_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this trading account"
        )

    account = db.query(Mt5InvestorAccount).filter(
        Mt5InvestorAccount.trading_account_id == trading_account_id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MT5 account not found"
        )

    if account.status != "CONNECTED":
        return Mt5SyncResponse(
            success=False,
            message=f"Account is not connected. Status: {account.status}"
        )

    investor_password = encryption_service.decrypt(account.encrypted_investor_password)
    mt5_client = MT5Client()
    success, error = mt5_client.connect(
        account.mt5_login,
        investor_password,
        account.mt5_server
    )

    if not success:
        account.status = "ERROR"
        account.error_message = error
        db.commit()
        return Mt5SyncResponse(
            success=False,
            message=f"Failed to connect to MT5: {error}"
        )

    from_time = account.last_sync_at or (datetime.now(pytz.UTC) - timedelta(days=30))
    to_time = datetime.now(pytz.UTC)

    deals = mt5_client.get_deals(from_time, to_time)
    mt5_client.disconnect()

    synced = 0
    skipped = 0
    errors = []

    deals_by_position = {}
    for deal in deals:
        position_id = deal.get("position_id", 0)
        if position_id == 0:
            continue
        if position_id not in deals_by_position:
            deals_by_position[position_id] = []
        deals_by_position[position_id].append(deal)

    for position_id, position_deals in deals_by_position.items():
        try:
            exit_deal = None
            entry_deal = None
            
            for deal in position_deals:
                entry_type = deal.get("entry")
                if entry_type == 0:
                    exit_deal = deal
                elif entry_type == 1:
                    entry_deal = deal
            
            if not exit_deal:
                continue
            
            terminal_trade_id = f"mt5_{position_id}_{exit_deal.get('ticket', 0)}"
            
            check_query = text("""
                SELECT id FROM trades
                WHERE "terminalTradeId" = :terminal_trade_id
            """)
            existing = db.execute(check_query, {"terminal_trade_id": terminal_trade_id}).fetchone()
            
            if existing:
                skipped += 1
                continue

            exit_time = datetime.fromtimestamp(exit_deal.get("time", 0), tz=pytz.UTC)
            entry_time = exit_time
            
            if entry_deal:
                entry_time = datetime.fromtimestamp(entry_deal.get("time", 0), tz=pytz.UTC)
            else:
                entry_time = exit_time - timedelta(hours=1)

            trade_type = "BUY" if exit_deal.get("type") == 0 else "SELL"
            quantity = abs(exit_deal.get("volume", 0))
            profit = exit_deal.get("profit", 0)

            insert_query = text("""
                INSERT INTO trades (
                    "tradingAccountId",
                    "terminalTradeId",
                    "terminalName",
                    "fromTerminal",
                    symbol,
                    type,
                    quantity,
                    "entryDate",
                    "exitDate",
                    profit,
                    pnl,
                    "createdAt",
                    "updatedAt"
                ) VALUES (
                    :trading_account_id,
                    :terminal_trade_id,
                    'mt5',
                    true,
                    :symbol,
                    :type,
                    :quantity,
                    :entry_date,
                    :exit_date,
                    :profit,
                    :profit,
                    NOW(),
                    NOW()
                )
            """)

            db.execute(insert_query, {
                "trading_account_id": trading_account_id,
                "terminal_trade_id": terminal_trade_id,
                "symbol": exit_deal.get("symbol", ""),
                "type": trade_type,
                "quantity": quantity,
                "entry_date": entry_time,
                "exit_date": exit_time,
                "profit": profit
            })
            synced += 1

        except Exception as e:
            errors.append(f"Error processing position {position_id}: {str(e)}")

    account.last_sync_at = to_time
    account.status = "CONNECTED"
    account.error_message = None
    db.commit()

    return Mt5SyncResponse(
        success=True,
        synced=synced,
        skipped=skipped,
        errors=errors,
        total=len(deals),
        message=f"Synced {synced} trades, skipped {skipped} duplicates"
    )


@router.delete("/disconnect/{trading_account_id}", response_model=DisconnectResponse)
async def disconnect_mt5(
    trading_account_id: int,
    token: str = Depends(get_authorization_token),
    db: Session = Depends(get_db)
):
    payload = verify_token(token)
    user_id = get_user_id_from_token(token)

    if not verify_trading_account_access(trading_account_id, user_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this trading account"
        )

    account = db.query(Mt5InvestorAccount).filter(
        Mt5InvestorAccount.trading_account_id == trading_account_id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MT5 account not found"
        )

    db.delete(account)
    db.commit()

    return DisconnectResponse(
        success=True,
        message="MT5 account disconnected and removed"
    )
