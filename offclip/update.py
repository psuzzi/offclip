"""Self-update from GitHub Releases: check, download, verify, switch, relaunch. Standard library only.

A new version is unpacked into <data>/app/<version>/ and recorded in <data>/current; the
bootstrap picks the newest app directory on the next start, so the installed copy is never touched.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import REPO, __version__
from .core import DATA_DIR, load_settings, save_settings

API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
USER_AGENT = f"offclip/{__version__}"
CHECK_EVERY = 24 * 3600


@dataclass
class Release:
    version: str
    tag: str
    notes: str
    page: str
    zip_url: str
    sums_url: Optional[str]


def parse_version(s: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", s)[:3]) or (0,)


def _get(url: str, timeout: int = 8, binary: bool = False) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "*/*" if binary else "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_latest() -> Optional[Release]:
    d = json.loads(_get(API_LATEST))
    tag = d.get("tag_name") or ""
    version = tag.lstrip("v")
    assets = {a.get("name"): a.get("browser_download_url") for a in d.get("assets", [])}
    zip_url = assets.get(f"offclip-{version}.zip")
    if not zip_url:
        return None
    return Release(version, tag, d.get("body") or "", d.get("html_url") or "", zip_url, assets.get("SHA256SUMS"))


def check(force: bool = False) -> Optional[Release]:
    """A newer release, or None (also on any network problem). Once a day unless forced."""
    s = load_settings()
    if not force and (not s.get("check_updates", True) or time.time() - float(s.get("last_update_check", 0)) < CHECK_EVERY):
        return None
    try:
        rel = fetch_latest()
    except Exception:
        return None
    s["last_update_check"] = time.time()
    save_settings(s)
    return rel if rel and parse_version(rel.version) > parse_version(__version__) else None


def apply(rel: Release, progress: Callable[[str], None] = lambda _s: None) -> Path:
    """Download and unpack `rel` into DATA_DIR/app/<version>, verify it, mark it current."""
    apps = DATA_DIR / "app"
    tmp = DATA_DIR / "tmp"
    apps.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)

    progress("downloading")
    data = _get(rel.zip_url, timeout=120, binary=True)
    if rel.sums_url:
        progress("verifying")
        name = f"offclip-{rel.version}.zip"
        sums = _get(rel.sums_url).decode("utf-8", "replace")
        expected = next((line.split()[0] for line in sums.splitlines() if line.strip().endswith(name)), None)
        if expected and expected.lower() != hashlib.sha256(data).hexdigest():
            raise RuntimeError("checksum mismatch: the download was discarded")

    progress("unpacking")
    zpath = tmp / f"offclip-{rel.version}.zip"
    zpath.write_bytes(data)
    stage = apps / f"{rel.version}.tmp"
    target = apps / rel.version
    shutil.rmtree(stage, ignore_errors=True)
    with zipfile.ZipFile(zpath) as z:
        for m in z.infolist():
            parts = Path(m.filename).parts
            if len(parts) < 2 or ".." in parts or parts[0].startswith("/"):
                continue                                   # strip the top-level folder, skip anything odd
            dest = stage.joinpath(*parts[1:])
            if m.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(m))
            if dest.suffix in (".sh", ".command"):
                dest.chmod(0o755)
    zpath.unlink(missing_ok=True)
    if not (stage / "offclip" / "__init__.py").exists():
        shutil.rmtree(stage, ignore_errors=True)
        raise RuntimeError("unexpected archive layout: update aborted")
    shutil.rmtree(target, ignore_errors=True)
    stage.rename(target)
    (DATA_DIR / "current").write_text(rel.version, "utf-8")
    for d in apps.iterdir():                               # keep the new one and the one we are running
        if d.is_dir() and d.name not in (rel.version, __version__):
            shutil.rmtree(d, ignore_errors=True)
    return target


def relaunch() -> bool:
    """Start the launcher again (the caller then closes the window). False if we do not know it."""
    launcher = os.environ.get("OFFCLIP_LAUNCHER")
    if not launcher or not Path(launcher).exists():
        return False
    if os.name == "nt":
        subprocess.Popen(["cmd", "/c", "start", "", launcher], creationflags=0x00000008 | 0x00000200, close_fds=True)
    else:
        subprocess.Popen(["bash", launcher], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True
