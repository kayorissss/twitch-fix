"""Точка входа TwitchFix.

Запуск из исходников:  python src/main.py  (или python -m src.main)
После установки:       twitchfix
Поддерживаются флаги:  --debug (подробный лог), --elevated (после UAC),
                       --version.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Позволяет запускать файл напрямую: `python src/main.py`.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def run(argv: list[str] | None = None) -> int:
    args = list(sys.argv if argv is None else argv)
    if "--version" in args:
        from src.config.constants import APP_NAME, APP_VERSION  # noqa: PLC0415

        print(f"{APP_NAME} v{APP_VERSION}")
        return 0
    from src.utils.logger import setup_logging  # noqa: PLC0415

    setup_logging(debug="--debug" in args)
    try:
        from src.app import TwitchFixApplication  # noqa: PLC0415
    except ImportError as exc:
        print(
            f"Cannot start TwitchFix: {exc}\nInstall dependencies: pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1

    app = TwitchFixApplication(args)
    app.window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
