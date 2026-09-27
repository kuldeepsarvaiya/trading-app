"""Rich-based logging utility for the intraday trading bot."""

import logging
import os
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(force_terminal=True, legacy_windows=False)


def setup_logger(name: str = "IntradayBot", log_level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    """Configures and returns a structured logger."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # Rich console handler for beautiful colored outputs
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
    )
    rich_handler.setLevel(level)
    logger.addHandler(rich_handler)

    if log_to_file:
        logs_dir = Path(__file__).resolve().parent.parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        file_path = logs_dir / "trading_bot.log"

        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
