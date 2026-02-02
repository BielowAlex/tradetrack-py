# TradeTrack MT5 Bridge

Клієнт для Windows від **TradeTrack**: підключає локальний MT5 до вашого акаунту на сайті. Синхронізація угод виконується **тільки по запиту з фронту** (кнопка «Отримати угоди») — без пулінгу.

## Вимоги

- Windows (MetaTrader5 Python працює тільки на Windows)
- Встановлений MT5 на цьому ж ПК
- Python 3.10+

## Встановлення

```bash
cd bridge
pip install -r requirements.txt
```

## Налаштування (конект з фронту)

**Рекомендований потік:** юзер запускає exe → з’являється вікно TradeTrack Sync зі статусом «Не підключено» → на **фронті** юзер відкриває розділ «Клієнт синхронізації», вводить дані і натискає **«Підключити»** → фронт відправляє конфіг на `http://localhost:8765/config` → bridge зберігає конфіг, статус змінюється на «Підключено». Угоди синхронізуються лише коли на сайті натиснуто **«Отримати угоди»** (фронт викликає `http://localhost:8765/sync-request`). Пулінгу немає.

**Що має зробити фронт для конекту:** при натисканні «Підключити» в розділі bridge відправити **POST** на `http://localhost:8765/config` з тілом (JSON):

- **api_base_url** — URL вашого сайту (наприклад `window.location.origin`)
- **sync_token** — Mt5Token для цього рахунку (з бекенду / tRPC)
- **trading_account_id** — CUID рахунку
- **mt5_login** — номер рахунку MT5 (число)
- **mt5_password** — інвестор-пароль MT5 (юзер вводить у формі на фронті)
- **mt5_server** — сервер MT5 (наприклад `Broker-Demo`)
- **mt5_path** — опційно, порожній рядок для автовизначення

Метод: `POST`, заголовок `Content-Type: application/json`. CORS на bridge дозволено (`*`). Якщо bridge не запущений, запит не пройде — покажіть юзеру повідомлення «Спочатку запустіть клієнт синхронізації на ПК».

**Якщо запускаєте через Python і хочете config вручну:** скопіюйте `config.example.json` у `config.json` і заповніть поля (або використовуйте конект з фронту, як вище).

## Запуск

- **Режим за замовчуванням (GUI, без пулінгу):** вікно з описом програми, статусом підключення та логом; сервер `http://127.0.0.1:8765` очікує тільки запити з фронту (`/config`, `/sync-request`):
  ```bash
  python main.py
  ```
- **Тільки конект і вихід** (консоль):
  ```bash
  python main.py --once
  ```
- **Один раз стягнути угоди і вийти** (консоль):
  ```bash
  python main.py --sync-only
  ```
- **Консоль: чекати перший /config і вийти** (для початкового налаштування):
  ```bash
  python main.py --no-gui
  ```

Можна запускати з кореня репо: `python bridge/main.py`.

**Перевірка статусу:** `GET http://localhost:8765/status` або `GET http://localhost:8765/` повертає JSON: `app`, `description`, `connected` (чи є збережений конфіг), `status`, `endpoints`.

## Потік (без пулінгу)

1. Запуск bridge → локальний сервер на 8765, GUI зі статусом «Не підключено» / «Підключено».
2. Фронт надсилає **POST /config** → bridge зберігає конфіг, статус «Підключено».
3. Коли юзер на сайті натискає «Отримати угоди», фронт викликає **GET або POST** `http://localhost:8765/sync-request` → bridge підключається до MT5, збирає угоди, **POST /api/mt5/sync/deals**, оновлює `state.json`, **POST /api/mt5/bridge/sync-done**. Пулінг не використовується.

## Що має реалізувати Next.js

- **POST /api/mt5/bridge/connected** — опційно, тіло `{ "trading_account_id": "<cuid>" }`, Bearer. Оновлення `bridgeConnectedAt` на TradingAccount (bridge за замовчуванням не викликає при /config; можна викликати з bridge при потребі).
- **POST /api/mt5/sync/request** — тіло `{ "trading_account_id": "<cuid>" }`, авторизація сесія. Встановити прапорець запиту синку (кнопка «Отримати угоди» на фронті викликає **локально** `http://localhost:8765/sync-request`, тож цей ендпоінт на Next.js опційний, якщо фронт не опитує сервер).
- **POST /api/mt5/sync/deals** — тіло `{ "trading_account_id": "<cuid>", "deals": [ ... ] }`, Bearer. Валідація Mt5Token, збереження угод.
- **POST /api/mt5/bridge/sync-done** — тіло `{ "trading_account_id": "<cuid>" }`, Bearer. Скинути прапорець після синку.
- **GET /api/mt5/bridge/pending-sync** — query `trading_account_id`, Bearer. Bridge викликає перед синком і використовує відповідь для визначення діапазону угод. Очікувана відповідь: `{ "sync_requested": bool, "requested_at": "ISO8601", "last_deal_at": "ISO8601" | null, "last_deal_ticket": number | null }`. Якщо є `last_deal_at` — bridge тягне угоди з MT5 лише після цього часу; якщо null — використовує локальний `last_sync_at` або 30 днів назад.

Формат **deals**: масив об’єктів з MT5 `history_deals_get` (snake_case): `ticket`, `position_id`, `time`, `entry`, `type`, `volume`, `profit`, `symbol` тощо. Якщо у вас processMt5Deals очікує camelCase — перетворіть на стороні Next.js.

## Збірка exe для розповсюдження (варіант 1 — один файл)

**Покрокова інструкція з командами:** дивіться **[BUILD.md](BUILD.md)** — там по кроках: відкрити термінал, перейти в `bridge`, встановити залежності, зібрати exe, де знайти файл і що робити далі.

**Коротко (на Windows, у папці проєкту):**

1. Відкрити термінал, перейти в папку `bridge`:
   ```powershell
   cd bridge
   ```
2. Встановити пакети і PyInstaller:
   ```powershell
   pip install -r requirements.txt pyinstaller
   ```
3. Зібрати один exe (numpy і MetaTrader5 — hidden-import для коректної збірки):
   ```powershell
   pyinstaller --onefile --name TradeTrackSync --hidden-import=numpy --hidden-import=MetaTrader5 main.py
   ```
4. Готовий файл лежить тут: **`bridge\dist\TradeTrackSync.exe`**. Його можна віддавати юзерам або викласти посилання на скачування на сайті.

**Поведінка exe для юзера:**
1. Юзер кладе `TradeTrackSync.exe` у будь-яку папку і запускає. Відкривається вікно **TradeTrack Sync** з описом програми та статусом «Не підключено».
2. Юзер відкриває **веб-ап** TradeTrack, розділ «Клієнт синхронізації», вводить MT5 логін/пароль/сервер і натискає **«Підключити»**. Фронт відправляє конфіг на `http://localhost:8765/config`. Статус у вікні змінюється на «Підключено».
3. Угоди синхронізуються лише коли на сайті натиснуто **«Отримати угоди»** (фронт викликає `http://localhost:8765/sync-request`). Пулінгу немає.

Файли `config.json` і `state.json` зберігаються в тій самій папці, де лежить exe.

**Розповсюдження:** на сайті кнопка «Завантажити клієнт синхронізації» → посилання на `TradeTrackSync.exe` (з релізів, Vercel Blob, S3 тощо).

## Файли

- `config.json` — не комітити (містить пароль MT5). Створюється після першого успішного конекту з фронту (POST на localhost:8765/config).
- `state.json` — зберігає `last_sync_at`; створюється автоматично під час синку.
