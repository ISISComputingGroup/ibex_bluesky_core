import os, sys
from ibex_bluesky_core.logger import logger

LOG_FOLDER = os.path.join("C:\\", "instrument", "var", "logs", "bluesky")
LOG_MESSAGE = "Logging something to test"
LOG_ENV_PATH = "BLUESKY_LOGS"
LOG_FILE_NAME = "blueskylogs.log"

def test_GIVEN_logging_is_requested_THEN_the_log_folder_exists():
    this_function_name = sys._getframe(  ).f_code.co_name
    message = LOG_MESSAGE + this_function_name
    # Log invocation.
    logger.blueskylogger.info(message);

    if (os.environ.__contains__(LOG_ENV_PATH)):
        assert os.path.exists(os.environ[LOG_ENV_PATH]) == False
    
    if (not os.environ.__contains__(LOG_ENV_PATH)):    
        assert os.path.exists(LOG_FOLDER) == True

def test_GIVEN_logging_is_requested_THEN_the_log_file_exists():
    log_path = LOG_FOLDER
    if (os.environ.__contains__(LOG_ENV_PATH)):
        log_path = os.environ[LOG_ENV_PATH]

    # Log invocation.
    this_function_name = sys._getframe(  ).f_code.co_name
    message = LOG_MESSAGE + this_function_name
    logger.blueskylogger.info(message);

    qualified_log_filename = os.path.join(log_path, LOG_FILE_NAME)
    assert os.path.exists(qualified_log_filename) == True

def test_GIVEN_logging_is_requested_THEN_the_log_file_contains_the_message():
    log_path = LOG_FOLDER
    if (os.environ.__contains__(LOG_ENV_PATH)):
        log_path = os.environ[LOG_ENV_PATH]

    # Log invocation.
    this_function_name = sys._getframe(  ).f_code.co_name
    message = LOG_MESSAGE + this_function_name
    logger.blueskylogger.info(message);

    qualified_log_filename = os.path.join(log_path, LOG_FILE_NAME)
    assert os.path.exists(qualified_log_filename) == True
    # Open the log file and read its content.
    with open(qualified_log_filename, 'r') as f:
        content = f.read()
        assert content.__contains__(message);

