import logging
import os
import sys
import time as _time
from contextlib import contextmanager
from typing import Iterator

_DIVIDER = "-" * 100
_LEVELS = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING, "ERROR": logging.ERROR}
# ANSI colors per level for console readability (auto-disabled when stdout isn't a terminal).
_COLORS = {logging.DEBUG: "\033[90m", logging.INFO: "\033[36m", logging.WARNING: "\033[33m", logging.ERROR: "\033[31m"}
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    def __init__(self, use_color: bool):
        super().__init__("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        color = _COLORS.get(record.levelno)
        return f"{color}{text}{_RESET}" if self._use_color and color else text


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("wellington_events")
    logger.setLevel(_LEVELS.get(os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
    if not logger.handlers:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(_ColorFormatter(use_color=sys.stdout.isatty()))
        logger.addHandler(console)
        # Optional file output: run with LOG_FILE=/path/to/run.log to also persist logs.
        log_file = os.getenv("LOG_FILE")
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            logger.addHandler(file_handler)
        logger.propagate = False
    return logger


class Logger:
    """Standardized logging for the scrapers — use instead of print().

    Levels (control globally with LOG_LEVEL=DEBUG|INFO|WARNING|ERROR):
        Logger.info("fetching ...")     normal progress
        Logger.warning("no image")      recoverable / skipped
        Logger.error("parse failed")    went wrong, run continues
        Logger.debug("raw: ...")        verbose detail (hidden unless LOG_LEVEL=DEBUG)
        Logger.exception("failed")      like error() but appends the traceback

    Helpers:
        Logger.set_source("Eventbrite") prefix every line with "[Eventbrite] "
        Logger.progress(3, 15, "page")  -> "[3/15] page"
        Logger.divider()                the "----" separator
        with Logger.timed("scrape"):    logs how long the block took

    Set LOG_FILE=<path> to also write logs to a file.
    """

    _logger = _build_logger()
    _source = ""

    @classmethod
    def set_source(cls, source: str) -> None:
        cls._source = source

    @classmethod
    def _fmt(cls, message: str) -> str:
        return f"[{cls._source}] {message}" if cls._source else message

    @classmethod
    def info(cls, message: str) -> None:
        cls._logger.info(cls._fmt(message))

    @classmethod
    def warning(cls, message: str) -> None:
        cls._logger.warning(cls._fmt(message))

    @classmethod
    def error(cls, message: str) -> None:
        cls._logger.error(cls._fmt(message))

    @classmethod
    def debug(cls, message: str) -> None:
        cls._logger.debug(cls._fmt(message))

    @classmethod
    def exception(cls, message: str) -> None:
        # Logs at ERROR level and appends the active exception's traceback. Call from an except block.
        cls._logger.exception(cls._fmt(message))

    @classmethod
    def progress(cls, current: int, total: int, label: str = "") -> None:
        cls._logger.info(cls._fmt(f"[{current}/{total}] {label}".rstrip()))

    @classmethod
    def divider(cls) -> None:
        cls._logger.info(_DIVIDER)

    @classmethod
    @contextmanager
    def timed(cls, label: str) -> Iterator[None]:
        start = _time.monotonic()
        cls.info(f"{label} — started")
        try:
            yield
        finally:
            cls.info(f"{label} — done in {_time.monotonic() - start:.1f}s")
