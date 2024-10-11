# *****************************************************************************
# Bluesky specific logging utility.
# *****************************************************************************

import os, logging, logging.config
import logging.handlers
from logging.handlers import TimedRotatingFileHandler
from bluesky.log import config_bluesky_logging
import pathlib

BLUESKY_LOGGER = 'bluesky'
DEFAULT_LOGGER = 'blueskylogs.log'
LOG_FOLDER = os.path.join("C:\\", "instrument", "var", "logs", BLUESKY_LOGGER)

# Find the log directory, if already set in the environment, else use the default
log_location = os.environ.get("BLUESKY_LOGS", LOG_FOLDER)
# Make the log directory if it doesn't already exist
os.makedirs(log_location, exist_ok = True)

filepath = pathlib.Path(__file__).resolve().parent
#disable_existing_loggers ensures all loggers have same configuration as below
logging.config.fileConfig(os.path.join(filepath, 'logging.conf'), disable_existing_loggers=False)

blueskylogger = logging.getLogger('root')

#This code only needed if disable_existing_loggers is removed from above and only chosen loggers are to be share the handler
#logging.config.fileConfig(os.path.join(filepath, 'logging.conf'))
#
#for handler in blueskylogger.handlers:
#    if isinstance(handler, logging.handlers.TimedRotatingFileHandler):
#        logger = logging.getLogger(BLUESKY_LOGGER)
#        if not logger.handlers:
#            logger.addHandler(handler)

