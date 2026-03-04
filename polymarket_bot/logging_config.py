import logging
from typing import Optional

from rich.logging import RichHandler


def configure_logging(level: int = logging.INFO, json: bool = False) -> None:
    """
    Configure application-wide logging.

    By default this sets up a Rich console handler suitable for local development.
    In production you may want to enable JSON logs and ship them to a log aggregator.
    """

    root = logging.getLogger()
    if root.handlers:
        # Avoid duplicate handlers when called multiple times.
        return

    if json:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        return

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Convenience wrapper."""

    return logging.getLogger(name if name else "polymarket_bot")

