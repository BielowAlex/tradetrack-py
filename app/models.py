from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Mt5InvestorAccount(Base):
    __tablename__ = "mt5_investor_accounts"

    id = Column(BigInteger, primary_key=True, index=True)
    trading_account_id = Column(BigInteger, ForeignKey("trading_accounts.id"), unique=True, nullable=False, index=True)
    mt5_login = Column(BigInteger, nullable=False)
    mt5_server = Column(String(255), nullable=False)
    encrypted_investor_password = Column(Text, nullable=False)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="DISCONNECTED", nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
