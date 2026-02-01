"""
GUI для TradeTrack Sync — вікно з описом програми, статусом підключення та логом.
Мова вибирається перед запуском (зберігається); в Налаштуваннях можна змінити мову — чинна після перезапуску.
"""
import queue
import sys
import webbrowser
from pathlib import Path
from typing import Callable, Optional

import tkinter as tk
from tkinter import ttk, scrolledtext

from config import get_language, save_language, has_saved_language
from i18n import LANG_UK, LANG_EN, get_text, SITE_URL_UK, SITE_URL_EN


def ask_language_at_startup() -> None:
    """Діалог вибору мови перед запуском. Показується лише при першому запуску; далі мова береться з state.json."""
    if has_saved_language():
        return
    dlg = tk.Tk()
    dlg.title("TradeTrack Sync — Оберіть мову / Select language")
    dlg.resizable(False, False)
    dlg.attributes("-topmost", True)
    f = tk.Frame(dlg, padx=24, pady=20)
    f.pack()
    tk.Label(f, text="Оберіть мову / Select language:", font=("Segoe UI", 10)).pack(pady=(0, 12))
    btn_frame = tk.Frame(f)
    btn_frame.pack()

    def choose(l: str) -> None:
        save_language(l)
        dlg.destroy()

    tk.Button(btn_frame, text="Українська", width=14, command=lambda: choose(LANG_UK)).pack(side=tk.LEFT, padx=6)
    tk.Button(btn_frame, text="English", width=14, command=lambda: choose(LANG_EN)).pack(side=tk.LEFT, padx=6)
    dlg.update_idletasks()
    dlg.geometry(f"+{dlg.winfo_screenwidth() // 2 - dlg.winfo_reqwidth() // 2}+{dlg.winfo_screenheight() // 2 - dlg.winfo_reqheight() // 2}")
    dlg.mainloop()


def create_window(
    msg_queue: queue.Queue,
    on_closing: Optional[Callable[[], None]] = None,
) -> tuple[tk.Tk, Callable[[str], None], Callable[[str], None]]:
    """Створити вікно з вкладками Головна та Налаштування. Повертає (root, set_status, append_log)."""
    root = tk.Tk()
    lang = get_language()
    root.title(get_text("app_title", lang))
    root.minsize(460, 440)
    root.geometry("520x460")

    if getattr(sys, "frozen", False):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).resolve().parent
    icon_path = base_dir / "icon.ico"
    if icon_path.exists():
        try:
            root.iconbitmap(str(icon_path))
        except Exception:
            pass

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    # Вкладка «Головна»
    tab_main = tk.Frame(notebook, padx=8, pady=8)
    notebook.add(tab_main, text=get_text("tab_main", lang))

    header = tk.Frame(tab_main, padx=4, pady=6)
    header.pack(fill=tk.X)
    tk.Label(header, text=get_text("app_title", lang), font=("Segoe UI", 14, "bold")).pack(anchor=tk.W)
    tk.Label(
        header,
        text=get_text("app_subtitle", lang),
        font=("Segoe UI", 9),
        fg="gray",
        wraplength=500,
        justify=tk.LEFT,
    ).pack(anchor=tk.W)
    tk.Label(
        header,
        text=get_text("app_instruction", lang),
        font=("Segoe UI", 8),
        fg="gray",
        wraplength=500,
        justify=tk.LEFT,
    ).pack(anchor=tk.W, pady=(6, 0))

    status_frame = tk.Frame(tab_main, padx=4, pady=8)
    status_frame.pack(fill=tk.X)
    tk.Label(status_frame, text=get_text("label_status", lang), font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
    status_var = tk.StringVar(value=get_text("status_waiting", lang))
    status_label = tk.Label(status_frame, textvariable=status_var, font=("Segoe UI", 9), fg="gray")
    status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    log_frame = tk.LabelFrame(tab_main, text=get_text("label_events", lang), padx=6, pady=6)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=8)
    log_text = scrolledtext.ScrolledText(
        log_frame,
        height=12,
        font=("Consolas", 9),
        wrap=tk.WORD,
        state=tk.DISABLED,
    )
    log_text.pack(fill=tk.BOTH, expand=True)

    site_frame = tk.Frame(tab_main, padx=4, pady=8)
    site_frame.pack(fill=tk.X)
    site_btn = tk.Button(
        site_frame,
        text=get_text("btn_open_site", lang),
        font=("Segoe UI", 9),
        cursor="hand2",
        command=lambda: webbrowser.open(SITE_URL_UK if get_language() == LANG_UK else SITE_URL_EN),
    )
    site_btn.pack()

    # Вкладка «Налаштування»
    tab_settings = tk.Frame(notebook, padx=16, pady=16)
    notebook.add(tab_settings, text=get_text("tab_settings", lang))

    settings_lang_row = tk.Frame(tab_settings)
    settings_lang_row.pack(fill=tk.X, pady=(0, 8))
    tk.Label(settings_lang_row, text=get_text("label_language", lang), font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
    lang_combo = ttk.Combobox(
        settings_lang_row,
        values=[get_text("lang_uk", lang), get_text("lang_en", lang)],
        state="readonly",
        width=16,
    )
    lang_combo.current(0 if lang == LANG_UK else 1)
    lang_combo.pack(side=tk.LEFT, padx=(10, 0))

    restart_hint_label = tk.Label(
        tab_settings,
        text="",
        font=("Segoe UI", 9),
        fg="gray",
        wraplength=400,
        justify=tk.LEFT,
    )
    restart_hint_label.pack(anchor=tk.W, pady=(12, 0))

    def _on_settings_lang_select(_event: object) -> None:
        idx = lang_combo.current()
        new_lang = LANG_UK if idx == 0 else LANG_EN
        if new_lang != get_language():
            save_language(new_lang)
            restart_hint_label.config(text=get_text("settings_restart_hint", new_lang), fg="gray")

    lang_combo.bind("<<ComboboxSelected>>", _on_settings_lang_select)

    def set_status(text: str, is_error: bool = False) -> None:
        status_var.set(text)
        status_label.config(fg="red" if is_error else "gray")

    def append_log(line: str) -> None:
        log_text.config(state=tk.NORMAL)
        log_text.insert(tk.END, line + "\n")
        log_text.see(tk.END)
        log_text.config(state=tk.DISABLED)

    def process_queue() -> None:
        try:
            while True:
                msg = msg_queue.get_nowait()
                if msg[0] == "status":
                    set_status(msg[1], is_error=msg[2] if len(msg) > 2 else False)
                elif msg[0] == "log":
                    append_log(msg[1])
        except queue.Empty:
            pass
        root.after(200, process_queue)

    def on_close() -> None:
        if on_closing:
            on_closing()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(200, process_queue)
    return root, set_status, append_log
