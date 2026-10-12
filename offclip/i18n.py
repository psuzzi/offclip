"""User-interface languages. English is the reference; Italian is the second language.

Adding a language: copy the "it" dictionary under a new code, translate the values, and add the code to
LANGUAGES. Missing keys fall back to English, so a partial translation still works.
The language follows the operating system unless settings.json says "language": "en" | "it".
"""
from __future__ import annotations

import locale
import os
import subprocess
import sys

LANGUAGES = {"en": "English", "it": "Italiano"}

STRINGS = {
    "en": {
        "title": "Download from YouTube",
        "add_link": "Add link",
        "search_label": "Looking for a video? Search on YouTube in your browser:",
        "search_btn": "Search",
        "paste_placeholder": "Paste a YouTube link here and press Enter, or drop links onto the table",
        "col_quality": "Quality", "col_link": "Link", "col_title": "Title", "col_channel": "Channel", "col_status": "Status",
        "hint_dnd": "No links yet. Drop them here, or paste one above.",
        "hint": "No links yet. Paste one above.",
        "choose_folder": "Choose folder…",
        "open_folder": "Open folder",
        "save_to": "Save to: {path}",
        "save_dialog": "Save downloads to…",
        "download": "Download",
        "max_rows": "At most {n} links at a time.",
        "st_fetching": "fetching info…", "st_ready": "ready", "st_error": "error", "st_done": "done ✓",
        "st_downloading": "downloading…", "st_processing": "processing…", "st_retrying": "retrying ({n}/{total})…",
        "tip_info": "Versions and updates", "tip_report": "Report a problem",
        "menu_file": "File", "menu_help": "Help", "menu_quit": "Quit", "menu_language": "Language", "menu_system": "System language",
        "menu_check": "Check for updates…", "menu_report": "Report a problem…", "menu_about": "About offclip",
        "language_changed": "The new language is used from the next start of offclip.",
        "tagline": "Save public clips for personal offline use.",
        "upd_available": "offclip {new} is available (you have {cur}).",
        "upd_latest": "You have the latest version.", "upd_latest_v": "You have the latest version ({cur}).",
        "upd_unknown": "No update known yet.",
        "upd_now": "Update now", "whats_new": "What's new", "check_updates": "Check for updates",
        "updating": "Updating… {stage}", "upd_downloading": "downloading", "upd_verifying": "verifying", "upd_unpacking": "unpacking",
        "upd_failed": "Update failed: {error}",
        "upd_done_restart": "Updated to {new}. offclip will now restart.",
        "upd_done_manual": "Updated to {new}. Please close and start offclip again.",
        "close": "Close", "cancel": "Cancel",
        "report_title": "Report a problem",
        "report_question": "What happened? A problem, an idea, a question.",
        "report_note": "Your text, the component versions and the last lines of the log are included. Nothing else is sent.",
        "report_send": "Send (opens GitHub)", "report_default_title": "Report from offclip",
    },
    "it": {
        "title": "Scarica da YouTube",
        "add_link": "Aggiungi link",
        "search_label": "Cerchi un video? Cerca su YouTube nel browser:",
        "search_btn": "Cerca",
        "paste_placeholder": "Incolla qui un link di YouTube e premi Invio, oppure trascina i link nella tabella",
        "col_quality": "Qualità", "col_link": "Link", "col_title": "Titolo", "col_channel": "Canale", "col_status": "Stato",
        "hint_dnd": "Nessun link per ora. Trascinali qui, oppure incollane uno qui sopra.",
        "hint": "Nessun link per ora. Incollane uno qui sopra.",
        "choose_folder": "Scegli cartella…",
        "open_folder": "Apri cartella",
        "save_to": "Salva in: {path}",
        "save_dialog": "Salva i download in…",
        "download": "Scarica",
        "max_rows": "Al massimo {n} link alla volta.",
        "st_fetching": "recupero info…", "st_ready": "pronto", "st_error": "errore", "st_done": "fatto ✓",
        "st_downloading": "scaricamento…", "st_processing": "elaborazione…", "st_retrying": "nuovo tentativo ({n}/{total})…",
        "tip_info": "Versioni e aggiornamenti", "tip_report": "Segnala un problema",
        "menu_file": "File", "menu_help": "Aiuto", "menu_quit": "Esci", "menu_language": "Lingua", "menu_system": "Lingua di sistema",
        "menu_check": "Cerca aggiornamenti…", "menu_report": "Segnala un problema…", "menu_about": "Informazioni su offclip",
        "language_changed": "La nuova lingua sarà usata dal prossimo avvio di offclip.",
        "tagline": "Salva clip pubbliche per uso personale offline.",
        "upd_available": "È disponibile offclip {new} (hai la {cur}).",
        "upd_latest": "Hai l'ultima versione.", "upd_latest_v": "Hai l'ultima versione ({cur}).",
        "upd_unknown": "Nessun aggiornamento noto per ora.",
        "upd_now": "Aggiorna ora", "whats_new": "Novità", "check_updates": "Cerca aggiornamenti",
        "updating": "Aggiornamento… {stage}", "upd_downloading": "scaricamento", "upd_verifying": "verifica", "upd_unpacking": "estrazione",
        "upd_failed": "Aggiornamento non riuscito: {error}",
        "upd_done_restart": "Aggiornato alla {new}. offclip verrà riavviato.",
        "upd_done_manual": "Aggiornato alla {new}. Chiudi e riapri offclip.",
        "close": "Chiudi", "cancel": "Annulla",
        "report_title": "Segnala un problema",
        "report_question": "Cosa è successo? Un problema, un'idea, una domanda.",
        "report_note": "Vengono inclusi il tuo testo, le versioni dei componenti e le ultime righe del log. Nient'altro viene inviato.",
        "report_send": "Invia (apre GitHub)", "report_default_title": "Segnalazione da offclip",
    },
}

_current = "en"


def detect_language() -> str:
    """The operating system's user-interface language, reduced to one of LANGUAGES (default "en")."""
    code = ""
    try:
        if sys.platform == "win32":
            import ctypes
            code = locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), "")
        elif sys.platform == "darwin":
            out = subprocess.run(["defaults", "read", "-g", "AppleLanguages"], capture_output=True, text=True, timeout=3).stdout
            for tok in out.replace("(", " ").replace(")", " ").replace(",", " ").replace('"', " ").split():
                code = tok
                break
    except Exception:
        code = ""
    if not code:
        for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
            if os.environ.get(var):
                code = os.environ[var]
                break
    if not code:
        try:
            code = locale.getlocale()[0] or ""
        except Exception:
            code = ""
    code = code.lower().replace("_", "-")
    for lang in LANGUAGES:
        if code.startswith(lang):
            return lang
    return "en"


def set_language(code: str) -> str:
    """Use `code` ("en", "it"), or the OS language for "auto"/unknown. Returns what is now in use."""
    global _current
    _current = code if code in LANGUAGES else detect_language()
    return _current


def current() -> str:
    return _current


def t(key: str, **kw) -> str:
    text = STRINGS.get(_current, {}).get(key) or STRINGS["en"].get(key) or key
    return text.format(**kw) if kw else text
