from __future__ import annotations

import logging
import sys

from .config import logs_dir


def configure_logging() -> None:
    logging.basicConfig(
        filename=logs_dir() / "app.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        encoding="utf-8",
    )


def main() -> int:
    configure_logging()
    from .gui import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())

