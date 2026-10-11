"""Tkinter window: paste up to 10 links, tick MP4/MP3 with a quality each, pick a folder, download."""
from __future__ import annotations

import sys
import threading
import traceback
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from . import REPO, __version__, core

ISSUES_URL = f"https://github.com/{REPO}/issues"
LINK_COLOR = "#1a56db"
BANNER_BG = "#dbeafe"     # light azure: the update notice must stand apart from the window, in light and dark mode
BANNER_FG = "#1e3a8a"


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
        self.lines: List[str] = []                     # in-memory log for the report dialog
        self._build()
        self.after(1500, lambda: self.check_updates(auto=True))

    # -- layout --------------------------------------------------------------
    def _build(self) -> None:
        top = ttk.Frame(self, padding=(12, 12, 12, 4))
        top.pack(fill="x")
        ttk.Label(top, text="Download from YouTube", font=("", 16, "bold")).pack(side="left")
        self._build_menu()

        # update banner: hidden until a newer release is found; its own colour so it is not mistaken for the app
        self.upd = tk.Frame(self, bg=BANNER_BG, padx=12, pady=8)
        self.upd_lbl = tk.Label(self.upd, text="", bg=BANNER_BG, fg=BANNER_FG, font=("", 12, "bold"))
        self.upd_lbl.pack(side="left")
        self.upd_btn = ttk.Button(self.upd, text="Update now", command=self.do_update)
        self.upd_btn.pack(side="left", padx=(14, 4))
        ttk.Button(self.upd, text="What's new", command=lambda: self.release and webbrowser.open(self.release.page)).pack(side="left", padx=4)
        ttk.Button(self.upd, text="Later", command=self.upd.pack_forget).pack(side="left", padx=4)
        self.release = None

        add = ttk.Frame(self, padding=(12, 4, 12, 8))
        add.pack(fill="x")
        self.add_frame = add
        self.url_var = tk.StringVar()
        entry = ttk.Entry(add, textvariable=self.url_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda _e: self.add_url())
        entry.focus_set()
        self.url_entry = entry
        self.add_btn = ttk.Button(add, text="Add link", command=self.add_url)
        self.add_btn.pack(side="left", padx=(8, 0))

        # bottom, from the bottom up: Download alone and centred; above it, Choose folder… then the path
        dl_row = ttk.Frame(self, padding=(12, 6, 12, 12))
        dl_row.pack(side="bottom", fill="x")
        self.dl_btn = ttk.Button(dl_row, text="Download", command=self.start_download, state="disabled")
        self.dl_btn.pack()
        folder_row = ttk.Frame(self, padding=(12, 6))
        folder_row.pack(side="bottom", fill="x")
        ttk.Button(folder_row, text="Choose folder…", command=self.choose_folder).pack(side="left")
        self.folder_lbl = ttk.Label(folder_row, text="", foreground="gray")
        self.folder_lbl.pack(side="left", padx=(10, 0))
        self._show_folder()

        # the table: a visible box with headers, an empty-state hint, and drag-and-drop of links
        box = tk.Frame(self, bd=1, relief="solid")
        box.pack(fill="both", expand=True, padx=12, pady=(0, 4))
        self.table = ttk.Frame(box, padding=(8, 6))
        self.table.pack(fill="both", expand=True)
        for c, h in enumerate(["MP4", "Quality", "MP3", "Quality", "Link", "Title", "Channel", "Status", ""]):
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
            apple.add_command(label="About offclip", command=self.help)
            apple.add_separator()
            bar.add_cascade(menu=apple)
        filem = tk.Menu(bar, tearoff=False)
        filem.add_command(label="Add link", accelerator="Cmd+L" if mac else "Ctrl+L", command=self._focus_entry)
        filem.add_command(label="Choose folder…", command=self.choose_folder)
        filem.add_separator()
        filem.add_command(label="Download", command=self.start_download)
        if not mac:
            filem.add_separator()
            filem.add_command(label="Quit", accelerator="Ctrl+Q", command=self.destroy)
        bar.add_cascade(label="File", menu=filem)
        helpm = tk.Menu(bar, name="help" if mac else None, tearoff=False)
        helpm.add_command(label="Check for updates…", command=self.check_updates)
        helpm.add_command(label="Report a problem…", command=self.report_problem)
        if not mac:
            helpm.add_separator()
            helpm.add_command(label="About offclip", command=self.help)
        bar.add_cascade(label="Help", menu=helpm)
        self.config(menu=bar)
        self.bind_all("<Command-l>" if mac else "<Control-l>", lambda _e: self._focus_entry())
        if not mac:
            self.bind_all("<Control-q>", lambda _e: self.destroy())

    def _focus_entry(self) -> None:
        self.url_entry.focus_set()
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
            self.url_var.set(url)
            self.add_url()

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
        self.hint.config(text="Drop links here, or paste one above and press Enter" if self.dnd_ok
                         else "Paste a link above and press Enter")
        self.hint.grid(row=1, column=0, columnspan=9, sticky="w", padx=4, pady=14)

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
        if not self.rows:
            self.hint.grid_remove()
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
        self._refresh_hint()
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
        messagebox.showinfo("About offclip", f"offclip {__version__}\nSave public clips for personal offline use.\n\n{v}")

    def report_problem(self) -> None:
        if messagebox.askyesno("Report a problem", "This opens the issue tracker in your browser.\n"
                               "Please include the link that failed and the versions shown under About."):
            webbrowser.open(ISSUES_URL)

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
            if not auto:
                messagebox.showinfo("offclip", f"You have the latest version ({__version__}).")
            return
        self.release = rel
        self.upd_lbl.config(text=f"offclip {rel.version} is available (you have {__version__}).")
        self.upd_btn.config(state="normal")
        self.upd.pack(fill="x", padx=12, pady=(0, 6), before=self.add_frame)

    def do_update(self) -> None:
        if not self.release or self.busy:
            return
        self.upd_btn.config(state="disabled")

        def work():
            from . import update
            try:
                update.apply(self.release, progress=lambda s: self.after(0, self.upd_lbl.config, {"text": f"Updating… {s}"}))
                self.after(0, self._update_done)
            except Exception as e:
                self.log(f"update failed: {e}")
                self.after(0, self.upd_lbl.config, {"text": f"Update failed: {str(e)[:120]}"})
                self.after(0, self.upd_btn.config, {"state": "normal"})
        threading.Thread(target=work, daemon=True).start()

    def _update_done(self) -> None:
        from . import update
        self.log(f"updated to {self.release.version}")
        if update.relaunch():
            messagebox.showinfo("offclip", f"Updated to {self.release.version}. offclip will now restart.")
            self.destroy()
        else:
            messagebox.showinfo("offclip", f"Updated to {self.release.version}. Please close and start offclip again.")

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
    app.after(1000, app.destroy)
    app.mainloop()
    print("selftest ok:", core.versions(), "| drag and drop:", "yes" if app.dnd_ok else "no")


def main() -> None:
    try:
        App().mainloop()
    except Exception:                                   # pythonw on Windows has no console: keep the trace
        with open(core.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise
