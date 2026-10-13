"""Screenshot the window in every language (or the codes given) at the minimum size, for reviewing translations.

    python scripts/screenshots.py OUT_DIR [code ...]

Needs Pillow (ImageGrab). Used by .github/workflows/screenshots.yml on Linux (xvfb), Windows and macOS; the PNGs are
uploaded as a workflow artifact. Rows are filled with fake metadata, no network. A language this Tk cannot show
falls back to English (gui.App._check_script); <code>-forced.png then shows it with that check disabled.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import ImageGrab  # noqa: E402

from offclip import gui, i18n  # noqa: E402


def shoot(code: str, out: Path, name: str = "") -> bool:
    """Save OUT/<code>.png; False when this Tk could not show the language (the window fell back to English)."""
    app = gui.App(language=code)
    app.after_cancel(app.auto_check)
    shown = i18n.current() == code
    gui._selftest_row(app, "https://youtu.be/aqz-KE-bpKQ")
    gui._selftest_row(app, "https://youtu.be/aqz-KE-bpKQ").finish([out / "x.mp3"])
    gui._selftest_row(app, "https://youtu.be/pending", fill=False)
    app.geometry("%dx%d+20+20" % gui.MIN_SIZE)
    for _ in range(20):
        app.update()
        time.sleep(0.05)
    x, y = app.winfo_rootx(), app.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height())).save(out / f"{name or code}.png")
    gui._selftest_close(app)
    return shown


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for code in sys.argv[2:] or list(i18n.LANGUAGES):
        if shoot(code, out):
            print("saved", out / f"{code}.png")
            continue
        check, gui.App._check_script = gui.App._check_script, lambda self: None   # what the fallback avoids
        shoot(code, out, f"{code}-forced")
        gui.App._check_script = check
        print("saved", out / f"{code}.png", "(English: this Tk cannot show it) and", out / f"{code}-forced.png")


if __name__ == "__main__":
    main()
