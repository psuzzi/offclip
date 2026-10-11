"""Second half of the bootstrap, run by whichever Python scripts/bootstrap.* found or fetched.

Standard library only; must run on Python 3.9. Prepares the per-user data folder:
  venv/        private environment with yt-dlp (and imageio-ffmpeg when no system ffmpeg exists)
  app/<ver>/   newer versions fetched by the self-updater; the newest one wins over the installed app
  state.json   what was set up, with which Python, when yt-dlp was last refreshed
and then starts the window (or the command line when arguments were given).
Exit code 3 means "this Python cannot create virtual environments": the shell side then retries
with a private Python.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

WIN = os.name == "nt"
DAY = 24 * 3600


class Splash:
    """A small window that mirrors the setup lines when there is no terminal to read them in
    (desktop launchers on Linux, pythonw on Windows). Silently absent when Tk is unavailable."""

    def __init__(self) -> None:
        self.root = None
        try:
            import tkinter as tk
            self.root = tk.Tk()
            self.root.title("offclip setup")
            self.root.geometry("640x220")
            self.text = tk.Text(self.root, font=("Menlo", 11) if sys.platform == "darwin" else ("monospace", 10),
                                relief="flat", padx=12, pady=10)
            self.text.pack(fill="both", expand=True)
            self.root.update()
        except Exception:
            self.root = None

    def line(self, s: str) -> None:
        if self.root is None:
            return
        try:
            self.text.insert("end", s + "\n")
            self.text.see("end")
            self.root.update()
        except Exception:
            self.root = None

    def close(self) -> None:
        if self.root is not None:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None


_splash: Optional[Splash] = None


def say(tag: str, msg: str) -> None:
    print(f"  [{tag}] {msg}", flush=True)
    if _splash is not None:
        _splash.line(f"[{tag}] {msg}")


def load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return {}


def version_of(app: Path) -> tuple:
    try:
        text = (app / "offclip" / "__init__.py").read_text("utf-8")
        m = re.search(r'__version__\s*=\s*"([^"]+)"', text)
        return tuple(int(x) for x in re.findall(r"\d+", m.group(1))[:3]) if m else (0,)
    except Exception:
        return (0,)


def choose_app(installed: Path, data: Path) -> Path:
    """The installed app, unless the self-updater left a newer one in data/app/<current>."""
    try:
        current = (data / "current").read_text("utf-8").strip()
    except Exception:
        return installed
    candidate = data / "app" / current
    if (candidate / "offclip" / "__init__.py").exists() and version_of(candidate) > version_of(installed):
        return candidate
    return installed


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if WIN else "bin/python")


def imports_ok(py: Path, modules: List[str]) -> bool:
    code = ";".join(f"import {m}" for m in modules) or "pass"
    return subprocess.run([str(py), "-c", code], capture_output=True).returncode == 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--app", required=True)
    ap.add_argument("--data", required=True)
    args, rest = ap.parse_known_args(argv)
    if rest and rest[0] == "--":
        rest = rest[1:]

    installed = Path(args.app).resolve()
    data = Path(args.data).resolve()
    data.mkdir(parents=True, exist_ok=True)

    global _splash
    no_tty = sys.stdout is None or not sys.stdout.isatty()
    if not rest and no_tty and not os.environ.get("OFFCLIP_NO_SPLASH"):
        _splash = Splash()           # the window is requested and nobody can read the console: show the lines in a box
    app = choose_app(installed, data)
    if app != installed:
        say("ok", f"Using updated version {'.'.join(map(str, version_of(app)))} from {app}")

    state_file = data / "state.json"
    state = load_json(state_file)
    venv = data / "venv"
    vpy = venv_python(venv)

    # --- 1. virtual environment ------------------------------------------------------------
    if not vpy.exists() or state.get("python") != sys.executable:
        say("++", f"Creating the Python environment in {venv}")
        shutil.rmtree(venv, ignore_errors=True)
        r = subprocess.run([sys.executable, "-m", "venv", str(venv)], capture_output=True, text=True)
        if r.returncode != 0 or not vpy.exists():
            say("!!", "This Python cannot create virtual environments.")
            if r.stderr.strip():
                print("       " + r.stderr.strip().splitlines()[-1])
            return 3
        state = {"python": sys.executable}
    else:
        say("ok", f"Python environment: {venv}")

    # --- 2. ffmpeg: use the system one when present ----------------------------------------
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        say("ok", f"ffmpeg: {system_ffmpeg} (already on this computer)")
    modules = ["yt_dlp"] + ([] if system_ffmpeg else ["imageio_ffmpeg"])

    # --- 3. yt-dlp (+ ffmpeg package when needed) ------------------------------------------
    req_files = [app / "requirements.txt"] + ([] if system_ffmpeg else [app / "requirements-ffmpeg.txt"])
    req_files = [f for f in req_files if f.exists()]
    digest = hashlib.sha256(b"".join(f.read_bytes() for f in req_files) + str(bool(system_ffmpeg)).encode()).hexdigest()
    if state.get("requirements") != digest or not imports_ok(vpy, modules):
        if system_ffmpeg:
            say("++", "Installing yt-dlp (about 3 MB)")
        else:
            say("++", "Installing yt-dlp and ffmpeg (about 25-35 MB)")
            say("  ", "because: no ffmpeg was found on this computer")
        cmd = [str(vpy), "-m", "pip", "install", "--quiet", "--disable-pip-version-check"]
        for f in req_files:
            cmd += ["-r", str(f)]
        if subprocess.call(cmd) != 0:
            say("!!", "Installation failed. Check the internet connection and start offclip again.")
            return 1
        state["requirements"] = digest
        state["ytdlp_checked"] = time.time()
    else:
        say("ok", "yt-dlp installed")

    # --- 4. keep yt-dlp fresh, once a day --------------------------------------------------
    if time.time() - float(state.get("ytdlp_checked", 0)) > DAY:
        say("..", "Checking for a yt-dlp update")
        r = subprocess.run([str(vpy), "-m", "pip", "install", "--quiet", "--upgrade", "--disable-pip-version-check",
                            "--timeout", "10", "--retries", "1", "yt-dlp"], capture_output=True)
        if r.returncode == 0:
            state["ytdlp_checked"] = time.time()
        else:
            say("..", "could not reach PyPI (offline?), will try again later")

    state_file.write_text(json.dumps(state, indent=2), "utf-8")
    say("ok", "ready")
    if _splash is not None:
        _splash.close()
        _splash = None

    # --- 5. launch ---------------------------------------------------------------------------
    env = dict(os.environ, OFFCLIP_APP=str(app), OFFCLIP_DATA=str(data), PYTHONPATH=str(app))
    if rest:                                               # command line / selftest: keep the console
        return subprocess.call([str(vpy), "-m", "offclip", *rest], cwd=str(app), env=env)
    if WIN:                                                # window without a console
        pyw = venv / "Scripts" / "pythonw.exe"
        exe = pyw if pyw.exists() else vpy
        subprocess.Popen([str(exe), "-m", "offclip"], cwd=str(app), env=env,
                         creationflags=0x00000008 | 0x00000200, close_fds=True)   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        return 0
    os.chdir(str(app))
    os.execve(str(vpy), [str(vpy), "-m", "offclip"], env)
    return 0                                               # not reached


def run() -> int:
    try:
        return main()
    finally:
        if _splash is not None:
            _splash.close()


if __name__ == "__main__":
    sys.exit(run())
