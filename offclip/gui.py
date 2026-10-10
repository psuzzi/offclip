"""Tkinter window: paste up to 10 links, tick MP4/MP3 with a quality each, pick a folder, download."""
from __future__ import annotations

import threading
import traceback
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from . import REPO, __version__, core

ISSUES_URL = f"https://github.com/{REPO}/issues"
LINK_COLOR = "#1a56db"


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
        self.status = add(ttk.Label(t, text="fetching info…", width=16), 7)
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
        self.status.config(text="ready", foreground="")
        self._sync()

    def fail(self, msg: str) -> None:
        self.status.config(text="error", foreground="red")
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
        self.outdir = self.settings.get("outdir") or core.default_outdir()
        self.rows: List[Row] = []
        self.busy = False
        self.lines: List[str] = []                     # in-memory log for a future report dialog
        self._build()

    # -- layout --------------------------------------------------------------
    def _build(self) -> None:
        top = ttk.Frame(self, padding=(12, 12, 12, 4))
        top.pack(fill="x")
        ttk.Label(top, text="Download from YouTube", font=("", 16, "bold")).pack(side="left")
        ttk.Button(top, text="?", width=3, command=self.help).pack(side="right")

        add = ttk.Frame(self, padding=(12, 4, 12, 8))
        add.pack(fill="x")
        self.url_var = tk.StringVar()
        entry = ttk.Entry(add, textvariable=self.url_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda _e: self.add_url())
        entry.focus_set()
        self.add_btn = ttk.Button(add, text="Add link", command=self.add_url)
        self.add_btn.pack(side="left", padx=(8, 0))

        bottom = ttk.Frame(self, padding=12)
        bottom.pack(fill="x", side="bottom")
        for c in range(3):
            bottom.columnconfigure(c, weight=1, uniform="b")
        self.folder_lbl = ttk.Label(bottom, text="", foreground="gray")
        self.folder_lbl.grid(row=0, column=0, sticky="w")
        self.dl_btn = ttk.Button(bottom, text="Download", command=self.start_download, state="disabled")
        self.dl_btn.grid(row=0, column=1)
        ttk.Button(bottom, text="Choose folder…", command=self.choose_folder).grid(row=0, column=2, sticky="e")
        self._show_folder()

        self.table = ttk.Frame(self, padding=(12, 0))
        self.table.pack(fill="both", expand=True)
        for c, h in enumerate(["MP4", "Quality", "MP3", "Quality", "Link", "Title", "Channel", "Status", ""]):
            ttk.Label(self.table, text=h, font=("", 10, "bold")).grid(row=0, column=c, sticky="w", padx=4, pady=(0, 6))
        self.table.columnconfigure(5, weight=3)
        self.table.columnconfigure(6, weight=1)

    # -- actions -------------------------------------------------------------
    def add_url(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            return
        if len(self.rows) >= core.MAX_ROWS:
            messagebox.showinfo("offclip", f"At most {core.MAX_ROWS} links at a time.")
            return
        if any(r.url == url for r in self.rows):
            self.url_var.set("")
            return
        self.url_var.set("")
        row = Row(self, len(self.rows), url)
        self.rows.append(row)
        self.refresh_buttons()
        threading.Thread(target=self._probe, args=(row,), daemon=True).start()

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
        self.refresh_buttons()

    def choose_folder(self) -> None:
        d = filedialog.askdirectory(initialdir=self.outdir, title="Save downloads to…")
        if d:
            self.outdir = d
            self.settings["outdir"] = d
            core.save_settings(self.settings)
            self._show_folder()

    def _show_folder(self) -> None:
        self.folder_lbl.config(text=f"Save to: {self.outdir}")

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
                self.after(0, row.set_status, text)

            try:
                files = core.download(row.clip, self.outdir, mp4_height=mp4, mp3_kbps=mp3, progress=progress)
                self.after(0, row.set_status, "done ✓", "green")
                self.log(f"saved {[str(f) for f in files]}")
            except Exception as e:
                msg = str(e).splitlines()[0][:200]
                self.after(0, row.set_status, "error", "red")
                self.after(0, row.title.config, {"text": f"{row.clip.title}\n{msg}"})
                self.log(f"download failed: {row.url}: {msg}")
        self.after(0, self._done)

    def _done(self) -> None:
        self.busy = False
        self.refresh_buttons()

    def help(self) -> None:
        v = "\n".join(f"{k}: {val}" for k, val in core.versions().items())
        if messagebox.askyesno("offclip", f"{v}\n\nReport a problem or an idea?\nThis opens the issue tracker in your browser."):
            webbrowser.open(ISSUES_URL)

    def log(self, line: str) -> None:
        self.lines.append(line)
        try:
            with open(core.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def main() -> None:
    try:
        App().mainloop()
    except Exception:                                   # pythonw on Windows has no console: keep the trace
        with open(core.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise
