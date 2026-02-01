-- Migration: Create mt5_investor_accounts table
-- Run this migration to create the MT5 investor accounts table in your PostgreSQL database

CREATE TABLE IF NOT EXISTS mt5_investor_accounts (
    id BIGSERIAL PRIMARY KEY,
    trading_account_id BIGINT NOT NULL UNIQUE,
    mt5_login BIGINT NOT NULL,
    mt5_server VARCHAR(255) NOT NULL,
    encrypted_investor_password TEXT NOT NULL,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL DEFAULT 'DISCONNECTED',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT fk_trading_account 
        FOREIGN KEY (trading_account_id) 
        REFERENCES trading_accounts(id) 
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mt5_investor_accounts_trading_account_id 
    ON mt5_investor_accounts(trading_account_id);

CREATE INDEX IF NOT EXISTS idx_mt5_investor_accounts_status 
    ON mt5_investor_accounts(status);

COMMENT ON TABLE mt5_investor_accounts IS 'Stores encrypted MT5 investor password credentials for trading accounts';
COMMENT ON COLUMN mt5_investor_accounts.encrypted_investor_password IS 'Fernet encrypted investor password';
COMMENT ON COLUMN mt5_investor_accounts.status IS 'Account status: CONNECTED, DISCONNECTED, ERROR';
