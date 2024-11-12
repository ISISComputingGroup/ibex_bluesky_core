import sys
from logging.handlers import TimedRotatingFileHandler

from ibex_bluesky_core.logger import logger

LOG_MESSAGE = "Logging something to "
LOG_FILE_NAME = "blueskylogs.log"


def test_GIVEN_logging_is_requested_THEN_handler_is_added():
    this_function_name = sys._getframe().f_code.co_name
    message = LOG_MESSAGE + this_function_name
    # Log invocation.
    logger.blueskylogger.info(message)

    loghandler = None
    for handler in logger.blueskylogger.handlers:
        if isinstance(handler, TimedRotatingFileHandler):
            loghandler = handler

    assert isinstance(loghandler, TimedRotatingFileHandler)
    assert loghandler is not None
    assert loghandler.name == "timedRotatingFileHandler"
    assert loghandler.baseFilename.endswith(LOG_FILE_NAME)
    assert loghandler is not None
