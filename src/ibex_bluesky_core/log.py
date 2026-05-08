"""Bluesky specific logging configuration.

.. note::
    :py:obj:`logging.config.fileConfig` sets the global, application-level, logging policies.
    :py:obj:`ibex_bluesky_core` is a library, so does not set application-level policies.
    Instead, handlers for our own logger and the bluesky loggers are added.
"""

import logging
import os
import sys
from functools import cache
from logging.handlers import TimedRotatingFileHandler

__all__ = ["file_handler", "set_bluesky_log_levels", "setup_logging"]

DEFAULT_LOG_FOLDER = os.path.join("C:\\", "instrument", "var", "logs", "bluesky")

# Find the log directory, if already set in the environment, else use the default
log_location = os.environ.get("IBEX_BLUESKY_CORE_LOGS", DEFAULT_LOG_FOLDER)

INTERESTING_LOGGER_NAMES = ["ibex_bluesky_core", "bluesky", "ophyd_async", "bluesky_kafka"]


@cache
def file_handler() -> TimedRotatingFileHandler:
    """Get the file handler for ibex_bluesky_core and related loggers.

    Cached so that this function does not run on import, but multiple invocations always return the
    same handler object.
    """
    handler = TimedRotatingFileHandler(os.path.join(log_location, "bluesky.log"), "midnight")

    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s (%(process)d) %(name)s %(filename)s "
            "[line:%(lineno)d] %(levelname)s %(message)s"
        ),
    )
    return handler


def setup_logging() -> None:
    r"""Set up logging with a default configuration.

    The default configuration is to log to ::

        c:\instrument\var\logs\bluesky

    This location can be overridden using the ``IBEX_BLUESKY_CORE_LOGS`` environment variable.

    Loggers listened-to by default include the loggers for this library, as well as
    the loggers for :py:obj:`bluesky` and :py:obj:`ophyd_async`. The severities of those
    loggers are set to ``INFO`` by default.
    """
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
