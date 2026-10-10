"""Entry point: `python -m offclip` opens the GUI, `python -m offclip URL...` runs the CLI."""
import sys


def main() -> None:
    if len(sys.argv) > 1:
        from .cli import main as cli_main
        sys.exit(cli_main(sys.argv[1:]))
    from .gui import main as gui_main
    gui_main()


if __name__ == "__main__":
    main()
