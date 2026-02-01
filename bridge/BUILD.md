# Як зібрати exe і що робити далі

## Крок 1: Відкрити термінал на Windows

- Натисніть **Win + R**, введіть `powershell`, Enter, або відкрийте **PowerShell** / **CMD** з меню Пуск.
- Або в Cursor/VS Code відкрийте термінал (Terminal → New Terminal).

---

## Крок 2: Активувати віртуальне середовище (щоб працював pip)

**Спочатку перейдіть у корінь проєкту** (папка `tradetrack-py`, де лежать `venv`, `app`, `bridge`):

```powershell
cd C:\Users\droho\WebstormProjects\tradetrack-py\tradetrack-py
```

Потім активуйте venv:

```powershell
.\venv\Scripts\Activate
```

Перед рядком із шляхом має з’явитися `(venv)` — тоді `pip` буде працювати.

---

## Крок 3: Перейти в bridge і встановити залежності

```powershell
cd bridge
pip install -r requirements.txt
pip install pyinstaller
```

**Якщо ви вже в папці `bridge` і не активували venv:** вийдіть у корінь, активуйте, поверніться:

```powershell
cd ..
.\venv\Scripts\Activate
cd bridge
pip install -r requirements.txt
pip install pyinstaller
```

**Якщо venv немає або pip все одно не знайдено:** спробуйте `python -m pip` замість `pip` (якщо Python встановлений глобально):

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

---

## Крок 4: Зібрати exe

Можна збирати з папки `bridge` або з кореня проєкту (spec знаходить `icon.ico` за абсолютним шляхом):

```powershell
cd bridge
pyinstaller TradeTrackSync.spec
```

Або з кореня проєкту:

```powershell
pyinstaller bridge\TradeTrackSync.spec
```

Або скрипт (переходить у `bridge` і збирає):

```powershell
.\bridge\build_exe.ps1
```

Spec: без консолі, іконка `icon.ico` (вікно, панель задач, іконка exe). Якщо в провіднику все ще стара іконка — Windows кешує іконки: скопіюйте exe в нову папку або перезавантажте провідник (закрийте всі вікна провідника й відкрийте знову).

Зачекайте 1–2 хвилини. У кінці має з’явитися щось на кшталт «Building EXE from EXE-00.toc completed successfully».

---

## Крок 5: Де лежить exe

Готовий файл:

```
bridge\dist\TradeTrackSync.exe
```

Тобто повний шлях, наприклад:

```
C:\Users\droho\WebstormProjects\tradetrack-py\tradetrack-py\bridge\dist\TradeTrackSync.exe
```

Відкрийте папку `bridge\dist` у провіднику — там один файл **TradeTrackSync.exe**. Це і є клієнт синхронізації.

---

## Після першого запуску exe — що робити (конект з фронту)

При першому запуску exe **не створює** config.json — він **чекає підключення з браузера**. Усі дані (токен, ID рахунку, MT5 логін/пароль/сервер) мають приходити **з вашого фронту**.

1. **Запустіть exe.** У консолі з’явиться щось на кшталт: «Bridge: waiting for connection from browser. Open your web app → bridge section → click Connect.»
2. **Відкрийте веб-ап** (ваш Next.js), перейдіть у розділ «Клієнт синхронізації» (або картка рахунку → bridge).
3. **На фронті** юзер вводить MT5 логін, інвестор-пароль, сервер (і при потребі обирає рахунок; токен і trading_account_id фронт бере з бекенду). Натискає **«Підключити»**.
4. **Фронт відправляє POST** на `http://localhost:8765/config` з тілом (JSON): `api_base_url`, `sync_token`, `trading_account_id`, `mt5_login`, `mt5_password`, `mt5_server`, `mt5_path` (опційно). Bridge зберігає конфіг і далі підключається до MT5, повідомить сервер і почне опитувати запити на синк.
5. Коли у веб-апі натиснуть «Отримати угоди», bridge стягне угоди з MT5 і відправить їх на сервер.

У терміналі побачите «Config received from browser. Connecting to MT5...», потім «Bridge connected», «Polling for sync requests». Щоб зупинити — закрийте вікно або Ctrl+C.

**Що реалізувати на фронті:** кнопка «Підключити» у розділі bridge має робити `fetch('http://localhost:8765/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ api_base_url, sync_token, trading_account_id, mt5_login, mt5_password, mt5_server, mt5_path: '' }) })`. Якщо запит не вдається (bridge не запущений), показати повідомлення: «Спочатку запустіть клієнт синхронізації на ПК».

---

## Крок 6: Що робити далі (розповсюдження)

### Варіант A: Віддати exe юзерам вручну

- Скопіюйте **TradeTrackSync.exe** з папки `dist` куди завгодно (на флешку, в архів, надіслати в месенджер).
- Юзер кладе exe в папку, при першому запуску створюється `config.json`, заповнює його, запускає exe знову — конектор працює.

### Варіант B: Посилання на скачування на сайті

1. Завантажте **TradeTrackSync.exe** туди, звідки можна його скачати:
   - GitHub Releases (створити реліз і прикріпити exe),
   - або хмара (Google Drive, Dropbox, Vercel Blob, S3 тощо).
2. Отримайте посилання на файл.
3. У веб-апі (Next.js) на сторінці «Клієнт синхронізації» додайте кнопку **«Завантажити клієнт синхронізації»**, яка веде на це посилання.

Юзер натискає кнопку → скачує один exe → кладе в папку → заповнює config.json (після першого запуску) → запускає — конектор працює.

---

## Якщо щось пішло не так

- **«pyinstaller не знайдено»** — виконайте ще раз: `pip install pyinstaller`, потім знову команду з кроку 4.
- **Помилка при збірці MetaTrader5** — збирайте на тому самому Windows-ПК, де встановлений MT5; Python і MT5 мають бути 64-bit (або обидва 32-bit).
- **Exe не запускається у юзера** — переконайтеся, що юзер на Windows і що поруч з exe після першого запуску з’явився `config.json` і він його заповнив.
- **MT5 -6 / «Terminal: Authorization failed»** — термінал не дозволяє підключення з Python API. Перевірте: (1) запускайте bridge від того ж користувача Windows, що й MT5 (не «від імені адміністратора», якщо MT5 звичайний); (2) у MT5: **Сервіс → Налаштування → Доп.** — увімкніть «Разрешить автоматическую торговлю» / Allow automated trading; (3) у config.json використовуйте саме **інвестор-пароль**, не основний пароль рахунку.
