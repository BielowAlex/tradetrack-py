# TradeTrack MT5 Integration API

Python FastAPI backend для інтеграції MetaTrader 5 з Next.js додатком через investor password.

## 🏗️ Архітектура

```
Next.js (UI + Auth) 
    ↓ REST API (JWT)
Python FastAPI Backend
    ↓ MetaTrader5 API (investor password)
MT5 Broker
    ↓
PostgreSQL (спільна БД)
```

## 📋 Вимоги

- Python 3.9+
- PostgreSQL база даних
- MetaTrader 5 terminal (для тестування) - **тільки на Windows**
  - ⚠️ **Важливо**: MetaTrader5 бібліотека доступна тільки для Windows
  - Для Linux: використовуйте Windows машину або Windows сервер для MT5 інтеграції
  - На Linux проект працюватиме, але MT5 endpoints повертатимуть помилку про відсутність бібліотеки

## 🚀 Встановлення

1. Створіть віртуальне середовище:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# або
venv\Scripts\activate  # Windows
```

2. Встановіть залежності:
```bash
# Для Linux (без MetaTrader5)
pip install -r requirements.txt

# Для Windows (з MetaTrader5)
pip install -r requirements-windows.txt
```

**Примітка**: `MetaTrader5` доступна тільки на Windows. На Linux встановіть тільки базові залежності.

3. Налаштуйте змінні оточення:
```bash
cp .env.example .env
# Відредагуйте .env файл з вашими налаштуваннями
```

4. Генеруйте Fernet ключ для шифрування:
```bash
python scripts/generate_fernet_key.py
```

Додайте згенерований ключ до `.env` як `ENCRYPTION_KEY_FERNET`.

5. Створіть таблицю в PostgreSQL (якщо ще не створена):
```sql
CREATE TABLE IF NOT EXISTS mt5_investor_accounts (
    id BIGSERIAL PRIMARY KEY,
    trading_account_id BIGINT NOT NULL UNIQUE REFERENCES trading_accounts(id),
    mt5_login BIGINT NOT NULL,
    mt5_server VARCHAR(255) NOT NULL,
    encrypted_investor_password TEXT NOT NULL,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL DEFAULT 'DISCONNECTED',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mt5_investor_accounts_trading_account_id 
ON mt5_investor_accounts(trading_account_id);
```

## 🏃 Запуск

```bash
python run.py
```

Або через uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API буде доступне на `http://localhost:8000`

## 📡 API Endpoints

### 1. POST /api/mt5/connect
Підключення до MT5 та збереження credentials.

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Body:**
```json
{
  "tradingAccountId": 1,
  "mt5Login": 12345678,
  "mt5Server": "Broker-Demo",
  "investorPassword": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "accountId": 1,
  "status": "CONNECTED",
  "message": "Successfully connected to MT5"
}
```

### 2. POST /api/mt5/sync/{tradingAccountId}
Синхронізація угод з MT5.

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Response:**
```json
{
  "success": true,
  "synced": 10,
  "skipped": 2,
  "errors": [],
  "total": 12,
  "message": "Synced 10 trades, skipped 2 duplicates"
}
```

### 3. GET /api/mt5/status/{tradingAccountId}
Отримати статус підключення.

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Response:**
```json
{
  "tradingAccountId": 1,
  "status": "CONNECTED",
  "mt5Login": 12345678,
  "mt5Server": "Broker-Demo",
  "lastSyncAt": "2024-01-15T10:30:00Z",
  "errorMessage": null
}
```

### 4. DELETE /api/mt5/disconnect/{tradingAccountId}
Відключення та видалення credentials.

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Response:**
```json
{
  "success": true,
  "message": "MT5 account disconnected and removed"
}
```

### 5. POST /api/mt5/test-connection
Тестування підключення без збереження.

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Body:**
```json
{
  "mt5Login": 12345678,
  "mt5Server": "Broker-Demo",
  "investorPassword": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "accountInfo": {
    "login": 12345678,
    "server": "Broker-Demo",
    "balance": 10000.0,
    "equity": 10050.0
  }
}
```

## 🔒 Безпека

- JWT автентифікація для всіх endpoints
- Investor password ніколи не повертається в API відповідях
- Всі паролі зашифровані в БД за допомогою Fernet
- Перевірка прав доступу (користувач може працювати тільки зі своїми accounts)

## 🔄 Синхронізація угод

- Використовує `mt5.history_deals_get()` для отримання угод
- Фільтрує тільки закриті угоди (DEAL_ENTRY_OUT)
- Перевіряє дублікати по `terminalTradeId`
- Зберігає в таблицю `trades` з полями:
  - `terminalTradeId`: "mt5_{positionId}_{ticket}"
  - `terminalName`: "mt5"
  - `fromTerminal`: true
  - `symbol`, `type`, `quantity`, `entryDate`, `exitDate`, `profit`, `pnl`

## 📁 Структура проекту

```
tradetrack-py/
├── app/
│   ├── __init__.py
│   ├── main.py              # Головний файл FastAPI
│   ├── config.py            # Конфігурація
│   ├── database.py          # Підключення до БД
│   ├── models.py            # SQLAlchemy моделі
│   ├── schemas.py           # Pydantic схеми
│   ├── auth.py              # JWT автентифікація
│   ├── encryption.py        # Шифрування паролів
│   ├── mt5_client.py        # MT5 клієнт
│   └── routers/
│       ├── __init__.py
│       └── mt5.py           # MT5 API endpoints
├── .env.example
├── requirements.txt
└── README.md
```

## 🧪 Тестування

Для тестування API використовуйте curl або Postman:

```bash
# Тест підключення
curl -X POST http://localhost:8000/api/mt5/test-connection \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mt5Login": 12345678,
    "mt5Server": "Broker-Demo",
    "investorPassword": "password123"
  }'
```

## ⚠️ Важливо

- Переконайтеся, що JWT_SECRET_KEY в Python backend співпадає з тим, що використовується в Next.js
- ENCRYPTION_KEY_FERNET повинен бути унікальним та безпечним
- MT5 terminal повинен бути встановлений для роботи з MetaTrader5 бібліотекою
- Для production використовуйте HTTPS та обмежте CORS origins
