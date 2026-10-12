"""Tkinter window. Map of this module:

  PlaceholderEntry  entry with a grey hint while empty
  ColorButton   flat coloured one-letter button (the yellow "?" and the "i" top right)
  Row           one pasted link: its widgets in the table, its probed metadata, its MP4/MP3 choices
  App           the window
    _build        layout, top to bottom: title + buttons, search strip (secondary), raised box = paste field + table + Download, folder row
    _build_menu   File / Help menu bar
    _setup_dnd    drag-and-drop of links onto the table (optional tkinterdnd2)
    add_url / remove / start_download / _download_all    the download flow (one at a time, background thread)
    show_info     dialog: versions, update notice (azure band), Update now
    report_problem dialog: description -> GitHub issue prefilled (relay comes later)
    check_updates / do_update    talk to offclip.update
  selftest      opens and closes the window; used by CI

Colours are constants at the top; every user-visible text comes from i18n.py via _t("key").
Everything that talks to yt-dlp lives in core.py, not here.
"""
from __future__ import annotations

import sys
import threading
import urllib.parse
from pathlib import Path
import traceback
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from . import REPO, __version__, core
from .i18n import t as _t
from . import i18n

ISSUES_URL = f"https://github.com/{REPO}/issues"
LINK_COLOR = "#1a56db"
BANNER_BG = "#dbeafe"     # light azure band for the update notice inside the info dialog
BANNER_FG = "#1e3a8a"
INFO_IDLE = ("#6b7280", "white")      # grey "i"
INFO_UPDATE = ("#2563eb", "white")    # blue "i" when a newer version exists
HELP_COLORS = ("#facc15", "#1f2937")  # yellow "?" with dark text


def _status_text(text: str) -> str:
    """core.download reports '42%', 'downloading', 'processing' or 'retrying 1/2': translate the words."""
    if text.startswith("retrying"):
        n, _, total = text.split()[-1].partition("/")
        return _t("st_retrying", n=n, total=total)
    return {"downloading": _t("st_downloading"), "processing": _t("st_processing")}.get(text, text)


class PlaceholderEntry(ttk.Entry):
    """ttk.Entry showing a grey hint while empty and unfocused."""

    def __init__(self, parent, textvariable: tk.StringVar, placeholder: str, **kw):
        super().__init__(parent, textvariable=textvariable, **kw)
        self.var, self.placeholder, self.showing = textvariable, placeholder, False
        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", self._focus_out)
        self._focus_out()

    def _focus_in(self, _e=None) -> None:
        if self.showing:
            self.var.set("")
            self.configure(foreground="")
            self.showing = False

    def _focus_out(self, _e=None) -> None:
        if not self.var.get():
            self.var.set(self.placeholder)
            self.configure(foreground="gray")
            self.showing = True

    def value(self) -> str:
        return "" if self.showing else self.var.get().strip()


class ColorButton(tk.Label):
    """A flat, coloured, one-character button (ttk buttons cannot be coloured on macOS/Windows).

    Change its look with set_colors((bg, fg)); that is all the update highlight does.
    """

    def __init__(self, parent, text: str, command, colors, tooltip: str = ""):
        super().__init__(parent, text=text, font=("", 13, "bold"), width=2, padx=6, pady=2, cursor="hand2", relief="flat")
        self.set_colors(colors)
        self.bind("<Button-1>", lambda _e: command())
        if tooltip:
            self.bind("<Enter>", lambda _e: self.configure(relief="raised"))
            self.bind("<Leave>", lambda _e: self.configure(relief="flat"))

    def set_colors(self, colors) -> None:
        self.configure(bg=colors[0], fg=colors[1], activebackground=colors[0])


class Row:
    """One pasted link: its widgets, its probed metadata, its choices."""

    def __init__(self, app: "App", index: int, url: str):
        self.app, self.url, self.clip = app, url, None
        t, r = app.table, index + 1
        self.mp4_on = tk.BooleanVar(value=False)
        self.mp3_on = tk.BooleanVar(value=True)
        self.w: List[tk.Widget] = []

        def add(widget, col, **grid):
            widget.grid(row=r, column=col, sticky=grid.pop("sticky", "w"), padx=4, pady=2, **grid)
            self.w.append(widget)
            return widget

        add(ttk.Checkbutton(t, variable=self.mp4_on, command=self._sync), 0)
        self.mp4_q = add(ttk.Combobox(t, width=7, state="disabled"), 1)
        add(ttk.Checkbutton(t, variable=self.mp3_on, command=self._sync), 2)
        self.mp3_q = add(ttk.Combobox(t, width=9, state="disabled"), 3)
        self.link = add(ttk.Label(t, text="…", foreground=LINK_COLOR, cursor="hand2"), 4)
        self.link.bind("<Button-1>", lambda _e: self.clip and webbrowser.open(self.clip.short_url))
        self.title = add(ttk.Label(t, text=url, wraplength=340), 5)
        self.channel = add(ttk.Label(t, text="", wraplength=160), 6)
        self.status = add(ttk.Label(t, text=_t("st_fetching"), width=16), 7)
        add(ttk.Button(t, text="×", width=2, command=lambda: app.remove(self)), 8)

    # -- state ---------------------------------------------------------------
    def fill(self, clip: core.Clip) -> None:
        self.clip = clip
        self.link.config(text=clip.short_url.replace("https://", ""))
        self.title.config(text=clip.title or clip.url)
        self.channel.config(text=clip.channel)
        self.mp4_q["values"] = [f"{h}p" for h in clip.video_heights] or ["best"]
        self.mp3_q["values"] = [f"{k} kbps" for k in clip.mp3_choices()]
        self.mp4_q.current(0)
        self.mp3_q.current(0)
        self.status.config(text=_t("st_ready"), foreground="")
        self._sync()

    def fail(self, msg: str) -> None:
        self.status.config(text=_t("st_error"), foreground="red")
        self.title.config(text=f"{self.url}\n{msg}")
        self.app.log(f"probe failed: {self.url}: {msg}")

    def _sync(self) -> None:
        ready = self.clip is not None
        self.mp4_q.config(state="readonly" if ready and self.mp4_on.get() else "disabled")
        self.mp3_q.config(state="readonly" if ready and self.mp3_on.get() else "disabled")
        self.app.refresh_buttons()

    def wants(self) -> bool:
        return self.clip is not None and (self.mp4_on.get() or self.mp3_on.get())

    def choices(self):
        mp4 = int(self.mp4_q.get().rstrip("p")) if self.mp4_on.get() and self.mp4_q.get() != "best" else (
            9999 if self.mp4_on.get() else None)
        mp3 = int(self.mp3_q.get().split()[0]) if self.mp3_on.get() else None
        return mp4, mp3

    def set_status(self, text: str, color: str = "") -> None:
        self.status.config(text=text, foreground=color)

    def regrid(self, index: int) -> None:
        for widget in self.w:
            widget.grid_configure(row=index + 1)

    def destroy(self) -> None:
        for widget in self.w:
            widget.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"offclip {__version__}")
        self.minsize(960, 460)
        self.settings = core.load_settings()
        i18n.set_language(self.settings.get("language", "auto"))
        self.outdir = self.settings.get("outdir") or core.default_outdir()
        self.rows: List[Row] = []
        self.busy = False
        self.lines: List[str] = []                     # in-memory log for the report dialog
        self._build()
        self.after(1500, lambda: self.check_updates(auto=True))

    # -- layout --------------------------------------------------------------
    def _build(self) -> None:
        top = ttk.Frame(self, padding=(12, 12, 12, 4))
        top.pack(fill="x")
        ttk.Label(top, text=_t("title"), font=("", 16, "bold")).pack(side="left")
        self._build_menu()
        self.info_btn = ColorButton(top, "i", self.show_info, INFO_IDLE, tooltip=_t("tip_info"))
        self.info_btn.pack(side="right", padx=(6, 0))
        self.help_btn = ColorButton(top, "?", self.report_problem, HELP_COLORS, tooltip=_t("tip_report"))
        self.help_btn.pack(side="right")
        self.release = None
        self.update_text = tk.StringVar(value="")
        self.info_win: Optional[tk.Toplevel] = None

        # secondary: a muted strip that sends a search to the system browser; offclip itself searches nothing
        search = ttk.Frame(self, padding=(12, 2, 12, 6))
        search.pack(fill="x")
        ttk.Label(search, text=_t("search_label"), foreground="gray").pack(side="left")
        self.search_var = tk.StringVar()
        sentry = ttk.Entry(search, textvariable=self.search_var, width=28)
        sentry.pack(side="left", padx=(8, 0))
        sentry.bind("<Return>", lambda _e: self.search_youtube())
        ttk.Button(search, text=_t("search_btn"), command=self.search_youtube).pack(side="left", padx=(6, 0))
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=12, pady=(2, 10))

        # bottom: the folder row, below the main box
        folder_row = ttk.Frame(self, padding=(12, 6, 12, 12))
        folder_row.pack(side="bottom", fill="x")
        ttk.Button(folder_row, text=_t("choose_folder"), command=self.choose_folder).pack(side="left")
        ttk.Button(folder_row, text=_t("open_folder"), command=self.open_folder).pack(side="right")
        self.folder_lbl = ttk.Label(folder_row, text="", foreground="gray")
        self.folder_lbl.pack(side="left", padx=(10, 0), fill="x", expand=True)
        self._show_folder()

        # the table: a visible box with headers, an empty-state hint, and drag-and-drop of links
        # the main box, raised like a card: paste field + tall Add button, the table, Download bottom-right
        ttk.Style(self).configure("Big.TButton", font=("", 13, "bold"), padding=(18, 10))
        box = tk.Frame(self, bd=2, relief="raised", padx=4, pady=4)
        box.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        add = ttk.Frame(box, padding=(8, 8, 8, 4))
        add.pack(fill="x")
        self.url_var = tk.StringVar()
        entry = PlaceholderEntry(add, textvariable=self.url_var, placeholder=_t("paste_placeholder"), font=("", 14))
        entry.pack(side="left", fill="both", expand=True, ipady=6)
        entry.bind("<Return>", lambda _e: self.add_url())
        self.url_entry = entry
        self.add_btn = ttk.Button(add, text=_t("add_link"), command=self.add_url, style="Big.TButton")
        self.add_btn.pack(side="left", padx=(8, 0), ipady=4)
        self.add_frame = add
        dl_row = ttk.Frame(box, padding=(8, 4, 8, 8))
        dl_row.pack(side="bottom", fill="x")
        self.dl_btn = ttk.Button(dl_row, text=_t("download"), command=self.start_download, state="disabled", style="Big.TButton")
        self.dl_btn.pack(side="right", ipady=4)
        self.table = ttk.Frame(box, padding=(8, 6))
        self.table.pack(fill="both", expand=True)
        for c, h in enumerate(["MP4", _t("col_quality"), "MP3", _t("col_quality"), _t("col_link"), _t("col_title"), _t("col_channel"), _t("col_status"), ""]):
            ttk.Label(self.table, text=h, font=("", 10, "bold")).grid(row=0, column=c, sticky="w", padx=4, pady=(0, 6))
        self.table.columnconfigure(5, weight=3)
        self.table.columnconfigure(6, weight=1)
        self.hint = ttk.Label(self.table, text="", foreground="gray")
        self._setup_dnd(box)
        self._refresh_hint()

    def _build_menu(self) -> None:
        """A minimal menu bar, replacing Tk's default one (which on macOS offers 'Run Widget Demo')."""
        mac = sys.platform == "darwin"
        bar = tk.Menu(self)
        if mac:                                   # the application menu: About goes here, Quit is added by macOS
            apple = tk.Menu(bar, name="apple", tearoff=False)
            apple.add_command(label=_t("menu_about"), command=self.show_info)
            apple.add_separator()
            bar.add_cascade(menu=apple)
        filem = tk.Menu(bar, tearoff=False)
        filem.add_command(label=_t("add_link"), accelerator="Cmd+L" if mac else "Ctrl+L", command=self._focus_entry)
        filem.add_command(label=_t("choose_folder"), command=self.choose_folder)
        filem.add_separator()
        filem.add_command(label=_t("download"), command=self.start_download)
        if not mac:
            filem.add_separator()
            filem.add_command(label=_t("menu_quit"), accelerator="Ctrl+Q", command=self.destroy)
        bar.add_cascade(label=_t("menu_file"), menu=filem)
        helpm = tk.Menu(bar, name="help" if mac else None, tearoff=False)
        helpm.add_command(label=_t("menu_check"), command=self.check_updates)
        helpm.add_command(label=_t("menu_report"), command=self.report_problem)
        langm = tk.Menu(helpm, tearoff=False)                    # Help > Language: System / English / Italiano
        self.lang_var = tk.StringVar(value=self.settings.get("language", "auto"))
        langm.add_radiobutton(label=_t("menu_system"), value="auto", variable=self.lang_var, command=self._set_language)
        for code, name in i18n.LANGUAGES.items():
            langm.add_radiobutton(label=name, value=code, variable=self.lang_var, command=self._set_language)
        helpm.add_cascade(label=_t("menu_language"), menu=langm)
        if not mac:
            helpm.add_separator()
            helpm.add_command(label=_t("menu_about"), command=self.show_info)
        bar.add_cascade(label=_t("menu_help"), menu=helpm)
        self.config(menu=bar)
        self.bind_all("<Command-l>" if mac else "<Control-l>", lambda _e: self._focus_entry())
        if not mac:
            self.bind_all("<Control-q>", lambda _e: self.destroy())

    def _set_language(self) -> None:
        self.settings["language"] = self.lang_var.get()
        core.save_settings(self.settings)
        messagebox.showinfo("offclip", _t("language_changed"))

    def _focus_entry(self) -> None:
        self.url_entry.focus_set()
        if not self.url_entry.showing:
            self.url_entry.select_range(0, "end")

    # -- drag and drop -----------------------------------------------------------
    def _setup_dnd(self, box: tk.Widget) -> None:
        """Accept links dropped from a browser onto the table. Needs the tkinterdnd2 package; optional."""
        self.dnd_ok = False
        try:
            from tkinterdnd2 import DND_ALL, TkinterDnD  # type: ignore
            TkinterDnD._require(self)                      # loads the tkdnd Tcl extension into this window
            wrapper = TkinterDnD.DnDWrapper
            for w in (box, self.table):
                wrapper.drop_target_register(w, DND_ALL)
                wrapper.dnd_bind(w, "<<Drop>>", self._on_drop)
            self.dnd_ok = True
        except Exception as e:                             # no package, or no tkdnd build for this Tk: paste still works
            self.log(f"drag and drop unavailable: {e}")

    def _on_drop(self, event) -> None:
        for url in self._urls_in(str(event.data)):
            self.url_entry._focus_in()        # leave placeholder mode, then add
            self.url_var.set(url)
            self.add_url()
        self.url_entry._focus_out()

    def _urls_in(self, data: str) -> List[str]:
        """URLs out of whatever the drag source handed over (Tcl list, uri-list, 'url\ntitle', …)."""
        try:
            items = list(self.tk.splitlist(data))
        except Exception:
            items = [data]
        urls: List[str] = []
        for item in items:
            for tok in item.replace("\r", "\n").split():
                tok = tok.strip("<>\"'")
                if tok.startswith(("http://", "https://")) and tok not in urls:
                    urls.append(tok)
        return urls

    def _refresh_hint(self) -> None:
        if self.rows:
            self.hint.grid_remove()
            return
        self.hint.config(text=_t("hint_dnd") if self.dnd_ok else _t("hint"))
        self.hint.grid(row=1, column=0, columnspan=9, sticky="w", padx=4, pady=14)

    # -- actions -------------------------------------------------------------
    def add_url(self) -> None:
        url = self.url_entry.value()
        if not url:
            return
        if len(self.rows) >= core.MAX_ROWS:
            messagebox.showinfo("offclip", _t("max_rows", n=core.MAX_ROWS))
            return
        if any(r.url == url for r in self.rows):
            self.url_var.set("")
            return
        self.url_var.set("")
        if self.focus_get() is not self.url_entry:
            self.url_entry._focus_out()
        if not self.rows:
            self.hint.grid_remove()
        row = Row(self, len(self.rows), url)
        self.rows.append(row)
        self.refresh_buttons()
        threading.Thread(target=self._probe, args=(row,), daemon=True).start()

    def search_youtube(self) -> None:
        words = self.search_var.get().strip()
        if not words:
            return
        webbrowser.open("https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": words}))
        self.search_var.set("")

    def _probe(self, row: Row) -> None:
        try:
            clip = core.probe(row.url)
            self.after(0, row.fill, clip)
        except Exception as e:
            self.after(0, row.fail, str(e).splitlines()[0][:200])

    def remove(self, row: Row) -> None:
        if self.busy:
            return
        row.destroy()
        self.rows.remove(row)
        for i, r in enumerate(self.rows):
            r.regrid(i)
        self._refresh_hint()
        self.refresh_buttons()

    def choose_folder(self) -> None:
        d = filedialog.askdirectory(initialdir=self.outdir, title=_t("save_dialog"))
        if d:
            self.outdir = d
            self.settings["outdir"] = d
            core.save_settings(self.settings)
            self._show_folder()

    def open_folder(self) -> None:
        try:
            Path(self.outdir).mkdir(parents=True, exist_ok=True)
            core.open_in_file_manager(self.outdir)
        except Exception as e:
            self.log(f"open folder failed: {e}")

    def _show_folder(self) -> None:
        self.folder_lbl.config(text=_t("save_to", path=self.outdir))

    def refresh_buttons(self) -> None:
        ok = (not self.busy) and any(r.wants() for r in self.rows)
        self.dl_btn.config(state="normal" if ok else "disabled")
        self.add_btn.config(state="disabled" if self.busy or len(self.rows) >= core.MAX_ROWS else "normal")

    def start_download(self) -> None:
        todo = [r for r in self.rows if r.wants()]
        if not todo:
            return
        self.busy = True
        self.refresh_buttons()
        threading.Thread(target=self._download_all, args=(todo,), daemon=True).start()

    def _download_all(self, rows: List[Row]) -> None:
        for row in rows:
            mp4, mp3 = row.choices()

            def progress(frac: Optional[float], text: str, row=row):
                self.after(0, row.set_status, _status_text(text))

            try:
                files = core.download(row.clip, self.outdir, mp4_height=mp4, mp3_kbps=mp3, progress=progress)
                self.after(0, row.set_status, _t("st_done"), "green")
                self.log(f"saved {[str(f) for f in files]}")
            except Exception as e:
                msg = str(e).splitlines()[0][:200]
                self.after(0, row.set_status, _t("st_error"), "red")
                self.after(0, row.title.config, {"text": f"{row.clip.title}\n{msg}"})
                self.log(f"download failed: {row.url}: {msg}")
        self.after(0, self._done)

    def _done(self) -> None:
        self.busy = False
        self.refresh_buttons()

    # -- info (versions + update) ----------------------------------------------
    def help(self) -> None:          # kept for the menu
        self.show_info()

    def show_info(self) -> None:
        if self.info_win is not None and self.info_win.winfo_exists():
            self.info_win.lift()
            return
        w = tk.Toplevel(self)
        w.title("offclip")
        w.resizable(False, False)
        w.transient(self)
        self.info_win = w
        body = ttk.Frame(w, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"offclip {__version__}", font=("", 15, "bold")).pack(anchor="w")
        ttk.Label(body, text=_t("tagline"), foreground="gray").pack(anchor="w", pady=(0, 10))
        mono = ("Menlo", 11) if sys.platform == "darwin" else ("Consolas", 10) if sys.platform == "win32" else ("monospace", 10)
        report = "\n".join(f"{k:8} {v}" for k, v in core.versions().items())
        txt = tk.Text(body, height=5, width=64, font=mono, relief="flat", wrap="none")
        txt.insert("1.0", report)
        txt.config(state="disabled")
        txt.pack(anchor="w")

        band = tk.Frame(body, bg=BANNER_BG, padx=12, pady=10)
        band.pack(fill="x", pady=(12, 0))
        self.update_lbl = tk.Label(band, textvariable=self.update_text, bg=BANNER_BG, fg=BANNER_FG, font=("", 12, "bold"), justify="left")
        self.update_lbl.pack(side="left", fill="x", expand=True)
        if self.release:
            self.update_text.set(_t("upd_available", new=self.release.version, cur=__version__))
            self.update_btn = ttk.Button(band, text=_t("upd_now"), command=self.do_update)
            self.update_btn.pack(side="left", padx=(10, 4))
            ttk.Button(band, text=_t("whats_new"), command=lambda: webbrowser.open(self.release.page)).pack(side="left")
        else:
            if not self.update_text.get():
                self.update_text.set(_t("upd_unknown") if not self.settings.get("last_update_check") else _t("upd_latest"))
            ttk.Button(band, text=_t("check_updates"), command=lambda: self.check_updates(auto=False)).pack(side="left", padx=(10, 0))

        foot = ttk.Frame(body)
        foot.pack(fill="x", pady=(14, 0))
        ttk.Button(foot, text=_t("menu_report"), command=self.report_problem).pack(side="left")
        ttk.Button(foot, text=_t("close"), command=w.destroy).pack(side="right")
        w.bind("<Escape>", lambda _e: w.destroy())

    # -- report a problem --------------------------------------------------------
    def report_problem(self) -> None:
        """Until the relay exists: a dialog that prepares a GitHub issue with the description and the context."""
        w = tk.Toplevel(self)
        w.title(_t("report_title"))
        w.transient(self)
        body = ttk.Frame(w, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=_t("report_question"), font=("", 13, "bold")).pack(anchor="w")
        ttk.Label(body, text=_t("report_note"),
                  foreground="gray", wraplength=520).pack(anchor="w", pady=(2, 8))
        text = tk.Text(body, height=8, width=70, wrap="word")
        text.pack(fill="both", expand=True)
        text.focus_set()
        foot = ttk.Frame(body)
        foot.pack(fill="x", pady=(12, 0))
        ttk.Button(foot, text=_t("cancel"), command=w.destroy).pack(side="right")

        def send():
            desc = text.get("1.0", "end").strip()
            title = (desc.splitlines() or [_t("report_default_title")])[0][:80]
            context = "\n".join(f"{k}: {v}" for k, v in core.versions().items())
            tail = "\n".join(self.lines[-25:])
            body_md = f"{desc}\n\n---\n```\n{context}\n```\n<details><summary>Last log lines</summary>\n\n```\n{tail}\n```\n</details>\n"
            url = f"{ISSUES_URL}/new?" + urllib.parse.urlencode({"title": title, "body": body_md[:6000]})
            webbrowser.open(url)
            w.destroy()

        ttk.Button(foot, text=_t("report_send"), command=send).pack(side="right", padx=(0, 8))
        w.bind("<Escape>", lambda _e: w.destroy())

    # -- self-update -----------------------------------------------------------
    def check_updates(self, auto: bool = False) -> None:
        def work():
            try:
                from . import update
                rel = update.check(force=not auto)
            except Exception as e:
                rel = None
                self.log(f"update check failed: {e}")
            self.after(0, self._update_result, rel, auto)
        threading.Thread(target=work, daemon=True).start()

    def _update_result(self, rel, auto: bool) -> None:
        if rel is None:
            self.update_text.set(_t("upd_latest_v", cur=__version__))
            if not auto and (self.info_win is None or not self.info_win.winfo_exists()):
                self.show_info()
            return
        self.release = rel
        self.update_text.set(_t("upd_available", new=rel.version, cur=__version__))
        self.info_btn.set_colors(INFO_UPDATE)          # the "i" turns blue: that is the update notice
        if not auto:
            if self.info_win is not None and self.info_win.winfo_exists():
                self.info_win.destroy()
            self.show_info()

    def do_update(self) -> None:
        if not self.release or self.busy:
            return
        try:
            self.update_btn.config(state="disabled")
        except Exception:
            pass

        def work():
            from . import update
            try:
                update.apply(self.release, progress=lambda st: self.after(0, self.update_text.set, _t("updating", stage=_t("upd_" + st))))
                self.after(0, self._update_done)
            except Exception as e:
                self.log(f"update failed: {e}")
                self.after(0, self.update_text.set, _t("upd_failed", error=str(e)[:120]))
                self.after(0, lambda: self.update_btn.config(state="normal"))
        threading.Thread(target=work, daemon=True).start()

    def _update_done(self) -> None:
        from . import update
        self.log(f"updated to {self.release.version}")
        if update.relaunch():
            messagebox.showinfo("offclip", _t("upd_done_restart", new=self.release.version))
            self.destroy()
        else:
            messagebox.showinfo("offclip", _t("upd_done_manual", new=self.release.version))

    def log(self, line: str) -> None:
        self.lines.append(line)
        try:
            with open(core.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def selftest() -> None:
    """Open the window, fill one fake row, close after a second. Used by CI."""
    app = App()
    app.hint.grid_remove()
    row = Row(app, 0, "https://youtu.be/aqz-KE-bpKQ")
    app.rows.append(row)
    assert app._urls_in("{https://youtu.be/aqz-KE-bpKQ} https://example.com/x\nTitle") == ["https://youtu.be/aqz-KE-bpKQ", "https://example.com/x"]
    row.fill(core.Clip(url="u", id="aqz-KE-bpKQ", title="Big Buck Bunny", channel="Blender",
                       short_url="https://youtu.be/aqz-KE-bpKQ", video_heights=[1080, 720], audio_kbps=[129, 66]))
    app.update()
    assert row.mp3_q["values"] and row.mp4_q["values"], "quality lists empty"
    assert app.dl_btn["state"] != "disabled", "download button should be enabled"
    app.info_btn.set_colors(INFO_UPDATE); app.update()
    app.after(1000, app.destroy)
    app.mainloop()
    i18n.set_language("it")
    assert _t("download") == "Scarica" and _status_text("retrying 1/2") == "nuovo tentativo (1/2)…"
    i18n.set_language("en")
    print("selftest ok:", core.versions(), "| drag and drop:", "yes" if app.dnd_ok else "no", "| language:", i18n.detect_language())


def main() -> None:
    try:
        App().mainloop()
    except Exception:                                   # pythonw on Windows has no console: keep the trace
        with open(core.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise
