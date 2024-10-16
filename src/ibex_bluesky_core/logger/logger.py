# *****************************************************************************
# Bluesky specific logging utility.
# To use me 
# 1. you need to import me --> from ibex_bluesky_core.logger import logger
# 2. Use me at the level you want --> logger.blueskylogger.info("Some useless message")
# 3. To change the log level check the logging.conf file
# *****************************************************************************

import os, logging, logging.config
import logging.handlers
import pathlib

BLUESKY_LOGGER = 'bluesky'
DEFAULT_LOGGER = 'blueskylogs.log'
LOG_FOLDER = os.path.join("C:\\", "instrument", "var", "logs", BLUESKY_LOGGER)

# Find the log directory, if already set in the environment, else use the default
log_location = os.environ.get("BLUESKY_LOGS", LOG_FOLDER)
# Create the log directory if it doesn't already exist
os.makedirs(log_location, exist_ok = True)

filepath = pathlib.Path(__file__).resolve().parent
#disable_existing_loggers ensures all loggers have same configuration as below
logging.config.fileConfig(os.path.join(filepath, 'logging.conf'), disable_existing_loggers=False)

blueskylogger = logging.getLogger('blueskycore')

