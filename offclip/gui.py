"""Tkinter window. Map of this module:

  fit_text      shorten a text to a width in pixels ("…" at the end); fit_middle cuts in the middle (paths)
  PlaceholderEntry  entry with a grey hint while empty
  ColorButton   flat coloured one-letter button (the yellow "?" and the "i" top right)
  Row           one pasted link: its widgets in the table, its probed metadata, its MP4/MP3 choices,
                after a download the saved files and the "open" link next to "done ✓" (finish / reveal);
                a done row is out of the Download set until a format is ticked again (_choice_changed)
  App           the window
    _build        layout, top to bottom: title + buttons, search strip (secondary), raised box = paste field + table
                  + Clear completed / Download, folder row
    _build_menu   File / Help menu bar
    _setup_dnd    drag-and-drop of links onto the table (optional tkinterdnd2)
    narrow windows  _fit_paste_hint (long or short hint, from the entry's width), _fit_titles (the Title column
                  takes the space the other columns leave; titles are cut to it), _show_folder (path cut in the middle)
    add_url / remove / clear_completed / start_download / _download_all    the download flow (one at a time, background thread)
    show_info     dialog: versions, update notice (azure band), Update now
    report_problem dialog: description -> GitHub issue prefilled (relay comes later)
    check_updates / do_update    talk to offclip.update
  selftest      opens the window, checks rows, Clear completed, the hint switch and the minimum size; used by CI

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
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from . import REPO, __version__, core
from .i18n import t as _t
from . import i18n

ISSUES_URL = f"https://github.com/{REPO}/issues"
LINK_LIGHT, LINK_DARK = "#1a56db", "#8ab4f8"        # link colour on a light / dark window background
MUTED_LIGHT, MUTED_DARK = "#6b6b6b", "#b0b0b0"       # secondary text
LINK_COLOR = LINK_LIGHT                               # set for real in App._pick_theme()
MUTED = MUTED_LIGHT
BANNER_BG = "#dbeafe"     # light azure band for the update notice inside the info dialog
BANNER_FG = "#1e3a8a"
INFO_IDLE = ("#6b7280", "white")      # grey "i"
INFO_UPDATE = ("#2563eb", "white")    # blue "i" when a newer version exists
HELP_COLORS = ("#facc15", "#1f2937")  # yellow "?" with dark text
MIN_SIZE = (960, 460)                 # smallest window; selftest checks that nothing is cut at this size
TITLE_MIN_PX = 120                    # the Title column never gets narrower than this
COLUMNS = 9                           # MP4, quality, MP3, quality, Link, Title, Channel, Status, ×
TITLE_COL, STATUS_COL = 5, 7


def _status_text(text: str) -> str:
    """core.download reports '42%', 'downloading', 'processing' or 'retrying 1/2': translate the words."""
    if text.startswith("retrying"):
        n, _, total = text.split()[-1].partition("/")
        return _t("st_retrying", n=n, total=total)
    return {"downloading": _t("st_downloading"), "processing": _t("st_processing")}.get(text, text)


def attach_tooltip(widget: tk.Widget, text_of) -> None:
    """Show `text_of()` in a small box while the pointer rests on `widget` (used for truncated titles)."""
    tip = {"win": None}

    def show(_e=None):
        text = text_of()
        if not text or tip["win"] is not None:
            return
        w = tk.Toplevel(widget)
        w.wm_overrideredirect(True)
        x, y = widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height() + 4
        w.wm_geometry(f"+{x}+{y}")
        tk.Label(w, text=text, justify="left", wraplength=520, relief="solid", borderwidth=1,
                 padx=8, pady=4, bg="#ffffe0", fg="#000000").pack()
        tip["win"] = w

    def hide(_e=None):
        if tip["win"] is not None:
            tip["win"].destroy()
            tip["win"] = None

    widget.bind("<Enter>", show)
    widget.bind("<Leave>", hide)
    widget.bind("<ButtonPress>", hide)


def shorten(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def fit_text(font: tkfont.Font, text: str, px: int) -> str:
    """The longest shorten(text, n) that is at most `px` pixels wide in `font`."""
    if font.measure(text) <= px:
        return text
    lo, hi = 1, len(text)                       # binary search on the number of characters kept
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.measure(shorten(text, mid)) <= px:
            lo = mid
        else:
            hi = mid - 1
    return shorten(text, lo)


def fit_middle(font: tkfont.Font, text: str, px: int) -> str:
    """Like fit_text, but keeps the start and the end: "/Users/me/…/Music/clips". For paths."""
    if font.measure(text) <= px:
        return text

    def cut(n: int) -> str:                     # keep n characters: a third at the start, the rest at the end
        head = n // 3
        return text[:head] + "…" + text[len(text) - (n - head):]

    lo, hi = 0, len(text) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.measure(cut(mid)) <= px:
            lo = mid
        else:
            hi = mid - 1
    return cut(lo)


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
            self.configure(foreground=MUTED)
            self.showing = True

    def set_placeholder(self, text: str) -> None:
        if text == self.placeholder:
            return
        self.placeholder = text
        if self.showing:
            self.var.set(text)

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
        self.files: List[Path] = []                  # what the last successful download saved
        self.done = False                            # True after a successful download: Clear completed removes it
        t, r = app.table, index + 1
        self.mp4_on = tk.BooleanVar(value=False)
        self.mp3_on = tk.BooleanVar(value=True)
        self.w: List[tk.Widget] = []

        def add(widget, col, **grid):
            widget.grid(row=r, column=col, sticky=grid.pop("sticky", "w"), padx=4, pady=2, **grid)
            self.w.append(widget)
            return widget

        add(ttk.Checkbutton(t, variable=self.mp4_on, command=self._choice_changed), 0)
        self.mp4_q = add(ttk.Combobox(t, width=7, state="readonly"), 1)
        add(ttk.Checkbutton(t, variable=self.mp3_on, command=self._choice_changed), 2)
        self.mp3_q = add(ttk.Combobox(t, width=9, state="readonly"), 3)
        self.link = add(ttk.Label(t, text="…", foreground=LINK_COLOR, cursor="hand2"), 4)
        self.link.bind("<Button-1>", lambda _e: self.clip and webbrowser.open(self.clip.short_url))
        self.full_title, self.full_channel = url, ""
        self.title = add(ttk.Label(t, text=""), TITLE_COL)
        self.set_title(url)
        self.channel = add(ttk.Label(t, text=""), 6)
        attach_tooltip(self.link, lambda: self.clip.short_url if self.clip else "")
        attach_tooltip(self.title, lambda: self.full_title)
        attach_tooltip(self.channel, lambda: self.full_channel)
        self._build_status(add(ttk.Frame(t), STATUS_COL))
        add(ttk.Button(t, text="×", width=2, command=lambda: app.remove(self)), 8)

    def _build_status(self, cell: ttk.Frame) -> None:
        """The Status cell: the status text, then "open" once a download is done; the progress bar replaces both."""
        self.status = ttk.Label(cell, text=_t("st_fetching"))
        self.status.grid(row=0, column=0, sticky="w")
        self.open_link = ttk.Label(cell, text=_t("open_file"), foreground=LINK_COLOR, cursor="hand2")
        self.open_link.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.open_link.grid_remove()                 # shown only after a successful download
        self.open_link.bind("<Button-1>", lambda _e: self.reveal())
        attach_tooltip(self.open_link, lambda: "\n".join([_t("tip_open_file")] + [f.name for f in self.files]))
        self.bar = ttk.Progressbar(cell, length=90, mode="determinate", maximum=100)
        self.bar.grid(row=0, column=0, columnspan=2, sticky="w")
        self.bar.grid_remove()                       # shown only while a download reports progress

    # -- state ---------------------------------------------------------------
    def fill(self, clip: core.Clip) -> None:
        self.clip = clip
        self.link.config(text=shorten(clip.id or clip.short_url.replace("https://", ""), 14))   # just the id; the link is the whole URL
        self.set_title(clip.title or clip.url)
        self.full_channel = clip.channel
        self.channel.config(text=shorten(clip.channel, 22))
        self.mp4_q["values"] = [f"{h}p" for h in clip.video_heights] or ["best"]
        self.mp3_q["values"] = [f"{k} kbps" for k in clip.mp3_choices()]
        self.mp4_q.current(0)
        self.mp3_q.current(0)
        self.status.config(text=_t("st_ready"), foreground="")
        self._sync()

    def fail(self, msg: str) -> None:
        self.status.config(text=_t("st_error"), foreground="red")
        self.set_title(f"{self.url}  —  {msg}")
        self.app.log(f"probe failed: {self.url}: {msg}")

    def set_title(self, text: str) -> None:
        self.full_title = text
        self.fit_title(self.app.title_px)

    def fit_title(self, px: int) -> None:
        self.title.config(text=fit_text(self.app.label_font, self.full_title, px))

    def _sync(self) -> None:
        """The quality list of a format is visible only while that format is ticked (and the clip is known)."""
        ready = self.clip is not None
        for on, combo in ((self.mp4_on.get(), self.mp4_q), (self.mp3_on.get(), self.mp3_q)):
            if ready and on:
                combo.grid()
            else:
                combo.grid_remove()
        self.app.refresh_buttons()
        self.app.refit_titles()                      # a quality list appearing or going changes the space left

    def _choice_changed(self) -> None:
        """A format ticked or unticked: a done row becomes ready again, so it can be downloaded with the new choice."""
        if self.done:
            self.done = False
            self.set_status(_t("st_ready"))
        self._sync()

    def wants(self) -> bool:
        """Is there something to download? Not for a done row: Download does not repeat finished work."""
        return self.clip is not None and not self.done and (self.mp4_on.get() or self.mp3_on.get())

    def choices(self):
        mp4 = int(self.mp4_q.get().rstrip("p")) if self.mp4_on.get() and self.mp4_q.get() != "best" else (
            9999 if self.mp4_on.get() else None)
        mp3 = int(self.mp3_q.get().split()[0]) if self.mp3_on.get() else None
        return mp4, mp3

    def set_status(self, text: str, color: str = "") -> None:
        self.bar.grid_remove()
        self.open_link.grid_remove()
        self.status.grid()
        self.status.config(text=text, foreground=color)

    def set_progress(self, frac: Optional[float], text: str) -> None:
        self.done = False
        if frac is None:
            self.set_status(text)
            return
        self.status.grid_remove()
        self.open_link.grid_remove()
        self.bar.grid()
        self.bar["value"] = max(0, min(100, int(frac * 100)))

    def finish(self, files: List[Path]) -> None:
        """A successful download: "done ✓", and "open" when there is a file to show."""
        self.files, self.done = list(files), True
        self.set_status(_t("st_done"), "green")
        if self.files:
            self.open_link.grid()
        self.app.refresh_buttons()

    def download_failed(self, msg: str) -> None:
        self.files, self.done = [], False
        self.set_status(_t("st_error"), "red")
        self.set_title(f"{self.clip.title}  —  {msg}")

    def reveal(self) -> None:
        """Show the saved file in Finder / Explorer (selected), or its folder in other file managers."""
        if not self.files:
            return
        try:
            core.reveal_in_file_manager(str(self.files[0]))
        except Exception as e:
            self.app.log(f"reveal failed: {e}")

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
        self.minsize(*MIN_SIZE)
        self.settings = core.load_settings()
        i18n.set_language(self.settings.get("language", "auto"))
        self.outdir = self.settings.get("outdir") or core.default_outdir()
        self.rows: List[Row] = []
        self.busy = False
        self.lines: List[str] = []                     # in-memory log for the report dialog
        self._build()
        self.after(1500, lambda: self.check_updates(auto=True))

    # -- layout --------------------------------------------------------------
    def _pick_theme(self) -> None:
        """Dark or light window background? Pick link and secondary-text colours that stay readable on it."""
        global LINK_COLOR, MUTED
        try:
            bg = ttk.Style(self).lookup("TFrame", "background") or self.cget("background")
            r, g, b = (v / 65535 for v in self.winfo_rgb(bg))
            dark = (0.299 * r + 0.587 * g + 0.114 * b) < 0.5
        except Exception:
            dark = False
        LINK_COLOR, MUTED = (LINK_DARK, MUTED_DARK) if dark else (LINK_LIGHT, MUTED_LIGHT)

    def _build(self) -> None:
        self._pick_theme()
        self.label_font = tkfont.nametofont("TkDefaultFont")    # what ttk labels use: titles are measured in it
        self.title_px = 360                                      # space for a title until the table has a size
        self._refit_pending = False
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
        ttk.Label(search, text=_t("search_label"), foreground=MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        sentry = ttk.Entry(search, textvariable=self.search_var, width=28)
        sentry.pack(side="left", padx=(8, 0))
        sentry.bind("<Return>", lambda _e: self.search_youtube())
        ttk.Button(search, text=_t("search_btn"), command=self.search_youtube).pack(side="left", padx=(6, 0))
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=12, pady=(2, 10))

        # bottom: the folder row, below the main box
        folder_row = ttk.Frame(self, padding=(12, 6, 12, 12))
        folder_row.pack(side="bottom", fill="x")
        self.choose_btn = ttk.Button(folder_row, text=_t("choose_folder"), command=self.choose_folder)
        self.choose_btn.pack(side="left")
        self.open_btn = ttk.Button(folder_row, text=_t("open_folder"), command=self.open_folder)
        self.open_btn.pack(side="right")
        self.folder_lbl = ttk.Label(folder_row, text="", foreground=MUTED)
        self.folder_lbl.pack(side="left", padx=(10, 0), fill="x", expand=True)
        attach_tooltip(self.folder_lbl, lambda: self.outdir)
        self.folder_row = folder_row
        folder_row.bind("<Configure>", lambda _e: self._show_folder())
        self._show_folder()

        # the table: a visible box with headers, an empty-state hint, and drag-and-drop of links
        # the main box, raised like a card: paste field + tall Add button, the table, Download bottom-right
        ttk.Style(self).configure("Big.TButton", font=("", 13, "bold"), padding=(14, 3))
        box = tk.Frame(self, bd=2, relief="raised", padx=4, pady=4)
        box.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        add = ttk.Frame(box, padding=(8, 8, 8, 4))
        add.pack(fill="x")
        self.url_var = tk.StringVar()
        entry = PlaceholderEntry(add, textvariable=self.url_var, placeholder=_t("paste_placeholder"), font=("", 13))
        entry.pack(side="left", fill="x", expand=True, ipady=2)
        entry.bind("<Return>", lambda _e: self.add_url())
        entry.bind("<Configure>", lambda e: self._fit_paste_hint(e.width))
        self.url_entry = entry
        self.entry_font = tkfont.Font(self, font=("", 13))
        self.add_btn = ttk.Button(add, text=_t("add_link"), command=self.add_url, style="Big.TButton")
        self.add_btn.pack(side="left", padx=(8, 0))
        self.add_frame = add
        dl_row = ttk.Frame(box, padding=(8, 4, 8, 8))
        dl_row.pack(side="bottom", fill="x")
        self.dl_btn = ttk.Button(dl_row, text=_t("download"), command=self.start_download, state="disabled", style="Big.TButton")
        self.dl_btn.pack(side="right")
        self.clear_lbl = ttk.Label(dl_row, text=_t("clear_completed"), foreground=MUTED, cursor="hand2")
        self.clear_lbl.bind("<Button-1>", lambda _e: self.clear_completed())   # quiet: shown only when there is something to clear
        self.table = ttk.Frame(box, padding=(8, 6))
        self.table.pack(fill="both", expand=True)
        for c, h in enumerate(["MP4", _t("col_quality"), "MP3", _t("col_quality"), _t("col_link"), _t("col_title"), _t("col_channel"), _t("col_status"), ""]):
            ttk.Label(self.table, text=h, font=("", 10, "bold")).grid(row=0, column=c, sticky="w", padx=4, pady=(0, 6))
        self.table.columnconfigure(TITLE_COL, weight=1)          # only Title stretches; the others keep their natural width
        self.table.columnconfigure(STATUS_COL, minsize=self.label_font.measure(_t("st_fetching")) + 16)
        self.table.bind("<Configure>", lambda _e: self.refit_titles())
        self.hint = ttk.Label(self.table, text="", foreground=MUTED)
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
        filem.add_command(label=_t("clear_completed"), command=self.clear_completed, state="disabled")
        self.file_menu, self.clear_item = filem, filem.index("end")
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
        self.bind_all("<Command-Return>" if mac else "<Control-Return>", lambda _e: self.start_download())
        self.bind_all("<Command-v>" if mac else "<Control-v>", self._paste_anywhere)
        if not mac:
            self.bind_all("<Control-q>", lambda _e: self.destroy())

    def _set_language(self) -> None:
        self.settings["language"] = self.lang_var.get()
        core.save_settings(self.settings)
        messagebox.showinfo("offclip", _t("language_changed"))

    def _paste_anywhere(self, event=None):
        """Cmd/Ctrl+V outside a text field: links in the clipboard become rows."""
        w = self.focus_get()
        if isinstance(w, (ttk.Entry, tk.Entry, tk.Text)):
            return None                               # let the field handle its own paste
        try:
            urls = self._urls_in(self.clipboard_get())
        except Exception:
            return None
        for url in urls:
            self.url_entry._focus_in()
            self.url_var.set(url)
            self.add_url()
        self.url_entry._focus_out()
        return "break" if urls else None

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

    # -- narrow windows ----------------------------------------------------------
    def _fit_paste_hint(self, width: int) -> None:
        """The long paste hint when it fits in the entry, the short one otherwise."""
        long = _t("paste_placeholder")
        fits = self.entry_font.measure(long) + 16 <= width
        self.url_entry.set_placeholder(long if fits else _t("paste_placeholder_short"))

    def _title_space(self) -> int:
        """Pixels left for a title: the table's width minus what the other columns ask for."""
        used = 0
        for c in range(COLUMNS):
            if c == TITLE_COL:
                continue
            widths = [w.winfo_reqwidth() + 8 for w in self.table.grid_slaves(column=c) if w is not self.hint]
            used += max(widths + [int(self.table.grid_columnconfigure(c, "minsize"))])
        return max(TITLE_MIN_PX, self.table.winfo_width() - 16 - used - 8 - 4)   # table padding, title padx, slack

    def refit_titles(self) -> None:
        """Cut every title to the Title column, once the pending layout is done."""
        if not self._refit_pending:
            self._refit_pending = True
            self.after_idle(self._fit_titles)

    def _fit_titles(self) -> None:
        self._refit_pending = False
        if not self.rows:
            return
        self.title_px = self._title_space()
        for row in self.rows:
            row.fit_title(self.title_px)

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
        self._drop([row])

    def clear_completed(self) -> None:
        """Remove the rows downloaded successfully; pending and failed ones stay."""
        self._drop([r for r in self.rows if r.done])

    def _drop(self, rows: List[Row]) -> None:
        if self.busy or not rows:
            return
        for row in rows:
            row.destroy()
            self.rows.remove(row)
        for i, r in enumerate(self.rows):
            r.regrid(i)
        self._refresh_hint()
        self.refresh_buttons()
        self.refit_titles()

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
        """'Save to: <path>', the path cut in the middle to the space between the two buttons."""
        width = self.folder_row.winfo_width()
        if width <= 1:                                   # not laid out yet: a guess that cannot widen the window
            width = MIN_SIZE[0]
        buttons = self.choose_btn.winfo_reqwidth() + self.open_btn.winfo_reqwidth()
        space = width - 24 - buttons - 10 - 8 - self.label_font.measure(_t("save_to", path=""))   # padding, gap, slack
        path = fit_middle(self.label_font, self.outdir, max(40, space))
        self.folder_lbl.config(text=_t("save_to", path=path))

    def refresh_buttons(self) -> None:
        ok = (not self.busy) and any(r.wants() for r in self.rows)
        self.dl_btn.config(state="normal" if ok else "disabled")
        self.add_btn.config(state="disabled" if self.busy or len(self.rows) >= core.MAX_ROWS else "normal")
        can_clear = (not self.busy) and any(r.done for r in self.rows)
        self.file_menu.entryconfigure(self.clear_item, state="normal" if can_clear else "disabled")
        if can_clear:
            self.clear_lbl.pack(side="right", padx=(0, 16))
        else:
            self.clear_lbl.pack_forget()

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
                self.after(0, row.set_progress, frac, _status_text(text))

            try:
                files = core.download(row.clip, self.outdir, mp4_height=mp4, mp3_kbps=mp3, progress=progress)
                self.after(0, row.finish, files)
                self.log(f"saved {[str(f) for f in files]}")
            except Exception as e:
                msg = str(e).splitlines()[0][:200]
                self.after(0, row.download_failed, msg)
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
    """Open the window, exercise the table without the network, close after a second. Used by CI."""
    import tempfile
    app = App()
    assert app._urls_in("{https://youtu.be/aqz-KE-bpKQ} https://example.com/x\nTitle") == ["https://youtu.be/aqz-KE-bpKQ", "https://example.com/x"]
    row = _selftest_row(app, "https://youtu.be/aqz-KE-bpKQ")
    app.update()
    assert row.mp3_q["values"] and row.mp4_q["values"], "quality lists empty"
    assert str(app.dl_btn["state"]) != "disabled", "download button should be enabled"
    _selftest_min_size(app)
    _selftest_long_folder(app)
    _selftest_done_row(app, row)
    _selftest_clear_completed(app, row, Path(tempfile.mkdtemp()) / "Big Buck Bunny [aqz-KE-bpKQ].mp3")
    _selftest_paste_hint(app)
    app.info_btn.set_colors(INFO_UPDATE); app.update()
    app.after(1000, app.destroy)
    app.mainloop()
    i18n.set_language("it")
    assert _t("download") == "Scarica" and _status_text("retrying 1/2") == "nuovo tentativo (1/2)…"
    assert _t("paste_placeholder_short") != STRINGS_EN["paste_placeholder_short"] and _t("clear_completed") != STRINGS_EN["clear_completed"]
    i18n.set_language("en")
    print("selftest ok:", core.versions(), "| drag and drop:", "yes" if app.dnd_ok else "no", "| language:", i18n.detect_language())


STRINGS_EN = i18n.STRINGS["en"]


def _selftest_row(app: App, url: str, fill: bool = True) -> Row:
    """A row as add_url makes it, filled with fake metadata instead of a probe."""
    row = Row(app, len(app.rows), url)
    app.rows.append(row)
    app._refresh_hint()
    if fill:
        row.fill(core.Clip(url=url, id="aqz-KE-bpKQ", title="Big Buck Bunny, the long title of an open movie made with Blender in 2008",
                           channel="Blender", short_url=url, video_heights=[1080, 720], audio_kbps=[129, 66]))
    return row


def _selftest_min_size(app: App) -> None:
    """At the minimum size, with both quality lists open, every control gets the width it asks for."""
    row = app.rows[0]
    row.mp4_on.set(True); row._sync()
    app.geometry("%dx%d" % MIN_SIZE); app.update(); app.update()
    cut = [w for w in (app.dl_btn, app.add_btn, app.info_btn, app.help_btn, *row.w)
           if w.winfo_ismapped() and w is not row.title and w.winfo_width() < w.winfo_reqwidth()]
    assert not cut, f"cut at {MIN_SIZE}: {[(str(w), w.winfo_width(), w.winfo_reqwidth()) for w in cut]}"
    right = app.winfo_rootx() + app.winfo_width()
    assert all(w.winfo_rootx() + w.winfo_width() <= right for w in row.w), "a column runs past the window"
    assert row.title.winfo_width() >= TITLE_MIN_PX, "no room left for the title"
    row.mp4_on.set(False); row._sync()


def _selftest_long_folder(app: App) -> None:
    """A long destination path is cut in the middle and leaves the folder buttons whole (#12)."""
    saved = app.outdir
    app.outdir = "/home/someone/" + "/".join(f"folder-number-{i}" for i in range(30)) + "/Music/clips"
    app._show_folder(); app.update()
    text = app.folder_lbl.cget("text")
    assert "…" in text and text.endswith("/Music/clips"), f"path not cut in the middle: {text}"
    assert app.folder_lbl.winfo_width() >= app.folder_lbl.winfo_reqwidth(), "path label is clipped"
    assert all(b.winfo_width() >= b.winfo_reqwidth() for b in (app.choose_btn, app.open_btn)), "folder buttons are cut"
    app.outdir = saved
    app._show_folder()


def _selftest_done_row(app: App, row: Row) -> None:
    """A done row is not downloaded again; ticking a format makes it ready again (#11)."""
    row.finish([]); app.update()
    assert not row.wants() and str(app.dl_btn["state"]) == "disabled", "Download would repeat a finished row"
    row.mp4_on.set(True); row._choice_changed(); app.update()
    assert not row.done and row.wants() and str(app.dl_btn["state"]) != "disabled", "ticking a format did not re-arm the row"
    row.mp4_on.set(False); row._choice_changed()


def _selftest_clear_completed(app: App, row: Row, saved: Path) -> None:
    """A finished row shows "open" and goes with Clear completed; a pending row stays; empty table shows the hint."""
    saved.write_bytes(b"")
    pending = _selftest_row(app, "https://youtu.be/pending", fill=False)
    row.finish([saved])
    app.update()
    assert row.done and row.files == [saved] and row.open_link.winfo_ismapped(), "finished row has no open link"
    assert app.clear_lbl.winfo_ismapped(), "Clear completed should be visible"
    app.clear_completed(); app.update()
    assert app.rows == [pending] and not app.hint.winfo_ismapped(), "Clear completed removed the wrong rows"
    assert not app.clear_lbl.winfo_ismapped(), "nothing left to clear"
    pending.finish([]); app.clear_completed(); app.update()
    assert not app.rows and app.hint.winfo_ismapped(), "the empty-table hint did not come back"


def _selftest_paste_hint(app: App) -> None:
    app._fit_paste_hint(200)
    assert app.url_entry.placeholder == _t("paste_placeholder_short")
    app._fit_paste_hint(4000)
    assert app.url_entry.placeholder == _t("paste_placeholder")
    if app.url_entry.showing:
        assert app.url_var.get() == _t("paste_placeholder")


def main() -> None:
    try:
        App().mainloop()
    except Exception:                                   # pythonw on Windows has no console: keep the trace
        with open(core.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise
