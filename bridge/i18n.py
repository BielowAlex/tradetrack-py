"""
Локалізація TradeTrack Sync — українська та англійська.
Модуль названо i18n (не locale), щоб не конфліктувати зі стандартною бібліотекою Python.
"""
from typing import Optional

LANG_UK = "uk"
LANG_EN = "en"
DEFAULT_LANG = LANG_UK

TEXTS: dict[str, dict[str, str]] = {
    "app_title": {"uk": "TradeTrack Sync", "en": "TradeTrack Sync"},
    "app_subtitle": {
        "uk": "Клієнт синхронізації MT5 з TradeTrack. Дозволяє передавати угоди з MetaTrader 5 у ваш журнал на сайті за запитом (кнопка «Отримати угоди»).",
        "en": "MT5 sync client for TradeTrack. Sends your MT5 trades to the journal on the site when you click «Get trades».",
    },
    "app_instruction": {
        "uk": (
            "Як підключити:\n"
            "1) Запустіть цю програму.\n"
            "2) На сайті TradeTrack: рахунок → MetaTrader 5 → «Клієнт синхронізації (bridge)».\n"
            "3) Введіть логін MT5, пароль і сервер → натисніть «Підключити».\n"
            "4) Після підключення на сайті натискайте «Отримати угоди», щоб синхронізувати угоди з MT5."
        ),
        "en": (
            "How to connect:\n"
            "1) Run this program.\n"
            "2) On TradeTrack site: account → MetaTrader 5 → «Sync client (bridge)».\n"
            "3) Enter MT5 login, password and server → click «Connect».\n"
            "4) After connecting, click «Get trades» on the site to sync deals from MT5."
        ),
    },
    "label_status": {"uk": "Статус:", "en": "Status:"},
    "label_events": {"uk": "Журнал подій", "en": "Event log"},
    "label_language": {"uk": "Мова:", "en": "Language:"},
    "lang_uk": {"uk": "Українська", "en": "Ukrainian"},
    "lang_en": {"uk": "English", "en": "English"},
    "status_waiting": {
        "uk": "Очікую підключення з сайту. Виконайте кроки інструкції вище в браузері.",
        "en": "Waiting for connection from the site. Follow the steps above in your browser.",
    },
    "status_connected": {
        "uk": "Підключено. Очікую натискання «Отримати угоди» на сайті.",
        "en": "Connected. Waiting for «Get trades» on the site.",
    },
    "status_syncing": {"uk": "Синхронізація угод…", "en": "Syncing deals…"},
    "status_mt5_error": {
        "uk": "Помилка підключення до MT5. Перевірте логін, пароль і сервер.",
        "en": "MT5 connection error. Check login, password and server.",
    },
    "log_started": {
        "uk": "Програма запущена. Очікую підключення з браузера.",
        "en": "Program started. Waiting for connection from browser.",
    },
    "log_enter_credentials": {
        "uk": "На сайті введіть логін MT5, пароль і сервер та натисніть «Підключити».",
        "en": "On the site enter MT5 login, password and server, then click «Connect».",
    },
    "log_config_from_browser": {"uk": "Конфіг отримано з браузера.", "en": "Config received from browser."},
    "log_config_saved": {"uk": "Конфіг збережено.", "en": "Config saved."},
    "log_server_notified": {
        "uk": "Сервер TradeTrack повідомлено про підключення.",
        "en": "TradeTrack server notified of connection.",
    },
    "log_server_notify_failed": {
        "uk": "Не вдалося повідомити сервер TradeTrack (перевірте мережу або URL).",
        "en": "Could not notify TradeTrack server (check network or URL).",
    },
    "log_sync_requested": {
        "uk": "Отримано запит «Отримати угоди» з сайту.",
        "en": "Received «Get trades» request from the site.",
    },
    "log_deals_sent": {
        "uk": "Угоди успішно відправлено на TradeTrack.",
        "en": "Deals sent to TradeTrack successfully.",
    },
    "log_sync_done": {"uk": "Синхронізація завершена.", "en": "Sync complete."},
    "log_error": {"uk": "Помилка:", "en": "Error:"},
    "msg_no_new_deals": {"uk": "Немає нових угод.", "en": "No new deals."},
    "msg_synced_n_deals": {"uk": "Синхронізовано {} угод.", "en": "Synced {} deals."},
    "msg_send_deals_failed": {
        "uk": "Не вдалося відправити угоди на сервер.",
        "en": "Failed to send deals to the server.",
    },
    "msg_mt5_connect_failed": {"uk": "Помилка підключення MT5: {}", "en": "MT5 connection failed: {}"},
    "msg_mt5_hint": {
        "uk": " (перевірте «Автоторгівля» в MT5 та інвестор-пароль)",
        "en": " (check «Allow automated trading» in MT5 and investor password)",
    },
    "lang_select_title": {"uk": "Оберіть мову", "en": "Select language"},
    "btn_open_site": {"uk": "Відкрити сайт TradeTrack", "en": "Open TradeTrack website"},
    "btn_contact": {"uk": "Контакт", "en": "Contact"},
    "api_description": {
        "uk": "Клієнт TradeTrack для підключення MT5 до акаунту на сайті. Синхронізація тільки по запиту з фронту.",
        "en": "TradeTrack client for connecting MT5 to your site account. Sync only on request from the frontend.",
    },
    "api_status_connected": {"uk": "Підключено (конфіг збережено)", "en": "Connected (config saved)"},
    "api_status_not_connected": {"uk": "Не підключено — надішліть конфіг з браузера", "en": "Not connected — send config from browser"},
    "api_config_endpoint": {"uk": "POST /config — підключення з браузера", "en": "POST /config — connect from browser"},
    "api_sync_endpoint": {"uk": "GET|POST /sync-request — отримати угоди (кнопка «Отримати угоди» на сайті)", "en": "GET|POST /sync-request — get deals (button «Get trades» on site)"},
    "tab_main": {"uk": "Головна", "en": "Main"},
    "tab_settings": {"uk": "Налаштування", "en": "Settings"},
    "settings_restart_hint": {
        "uk": "Зміна мови набуде чинності після перезапуску програми.",
        "en": "Language change will take effect after you restart the program.",
    },
}

SITE_URL_UK = "https://www.tradetrack.space/uk"
SITE_URL_EN = "https://www.tradetrack.space/en"
SITE_CONTACT_URL_UK = "https://www.tradetrack.space/uk/contact"
SITE_CONTACT_URL_EN = "https://www.tradetrack.space/en/contact"


def get_text(key: str, lang: Optional[str] = None) -> str:
    """Повертає рядок для ключа та мови. Якщо lang None — використовується DEFAULT_LANG."""
    l = lang or DEFAULT_LANG
    if l not in ("uk", "en"):
        l = DEFAULT_LANG
    return TEXTS.get(key, {}).get(l, TEXTS.get(key, {}).get(DEFAULT_LANG, key))
