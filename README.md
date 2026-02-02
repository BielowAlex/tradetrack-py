# TradeTrack MT5 Bridge

Репозиторій містить лише **TradeTrack MT5 Bridge** — клієнт для Windows, що підключає локальний MT5 до вашого акаунту на сайті. Синхронізація угод виконується **тільки по запиту з фронту** (кнопка «Отримати угоди»), без пулінгу.

Детальна документація, встановлення, налаштування та збірка exe — у папці **[bridge](bridge/)**:

- **[bridge/README.md](bridge/README.md)** — опис, вимоги, встановлення, налаштування з фронту, запуск, збірка exe
- **[bridge/BUILD.md](bridge/BUILD.md)** — покрокова збірка exe для розповсюдження

## Швидкий старт

```bash
cd bridge
pip install -r requirements.txt
python main.py
```

Сервер bridge: `http://127.0.0.1:8765` (ендпоінти `/config`, `/sync-request`, `/status`).
