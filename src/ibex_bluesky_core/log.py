"""Bluesky specific logging configuration.

Note: logging.config.fileconfig sets the global, application-level, logging policies. We are a
library so should not set application-level policies. Instead just quietly add handlers for our own
logger and the bluesky logger.
"""

import logging.config
import os
import sys
from functools import cache
from logging import Formatter
from logging.handlers import TimedRotatingFileHandler

__all__ = ["setup_logging", "set_bluesky_log_levels", "file_handler"]

DEFAULT_LOG_FOLDER = os.path.join("C:\\", "instrument", "var", "logs", "bluesky")

# Find the log directory, if already set in the environment, else use the default
log_location = os.environ.get("IBEX_BLUESKY_CORE_LOGS", DEFAULT_LOG_FOLDER)

INTERESTING_LOGGER_NAMES = ["ibex_bluesky_core", "bluesky", "ophyd_async"]


@cache
def file_handler() -> TimedRotatingFileHandler:
    """Get the file handler for ibex_bluesky_core and related loggers.

    Cached so that this function does not run on import, but multiple invocations always return the
    same handler object.
    """
    handler = TimedRotatingFileHandler(os.path.join(log_location, "bluesky.log"), "midnight")

    handler.setFormatter(
        Formatter(
            "%(asctime)s (%(process)d) %(name)s %(filename)s "
            "[line:%(lineno)d] %(levelname)s %(message)s"
        ),
    )
    return handler


def setup_logging() -> None:
    """Set up logging."""
    # Create the log directory if it doesn't already exist
    try:
        os.makedirs(log_location, exist_ok=True)
    except OSError:
        print("unable to create ibex_bluesky_core log directory", file=sys.stderr)
        return

    # We only want messages from bluesky, ophyd_async, and ibex_bluesky_core in our logs, not
    # messages from the root logger or other libraries.
    for name in INTERESTING_LOGGER_NAMES:
        logging.getLogger(name).addHandler(file_handler())

    set_bluesky_log_levels()


def set_bluesky_log_levels(level: str | int | None = None) -> None:
    """Set log level of bluesky-related loggers: ibex_bluesky_core, bluesky & ophyd_async.

    Args:
        level: a log level string or integer, or None. If None, will set INFO level by default for
            loggers which have not previously been configured, but will not change log levels for
            already-configured loggers.

    """
    for name in INTERESTING_LOGGER_NAMES:
        logger = logging.getLogger(name)
        if level is None and logger.level == logging.NOTSET:
            level = "INFO"

        if level is not None:
            logger.setLevel(level)
