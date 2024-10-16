import os, sys
import logging
from ibex_bluesky_core.logger import logger

LOG_FOLDER = os.path.join("C:\\", "instrument", "var", "logs", "bluesky")
LOG_MESSAGE = "Logging something to "
LOG_ENV_PATH = "BLUESKY_LOGS"
LOG_FILE_NAME = "blueskylogs.log"

def test_GIVEN_logging_is_requested_THEN_handler_is_added():
    this_function_name = sys._getframe(  ).f_code.co_name
    message = LOG_MESSAGE + this_function_name
    # Log invocation.
    logger.blueskylogger.info(message);

    logHandler = None
    for handler in logger.blueskylogger.handlers:
        if isinstance(handler, logging.handlers.TimedRotatingFileHandler):
            logHandler = handler

    assert handler is not None
    assert handler.name == 'timedRotatingFileHandler'
    assert handler.when.lower() == 'midnight'
    assert handler.baseFilename.endswith(LOG_FILE_NAME) == True

 