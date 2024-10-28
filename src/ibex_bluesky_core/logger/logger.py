"""Bluesky specific logging utility."""

import logging
import logging.config
import os
from pathlib import Path

"""Logger for bluesky. Loads the configured log handler and also attaches to default bluesky logger
To use me
1. you need to import me --> from ibex_bluesky_core.logger import logger
2. Use me at the level you want --> logger.blueskylogger.info("Some useful message")
3. To change the log level check the logging.conf file"""

BLUESKY_LOGGER = "bluesky"
DEFAULT_LOGGER = "blueskylogs.log"
LOG_FOLDER = os.path.join("C:\\", "instrument", "var", "logs", BLUESKY_LOGGER)

# Find the log directory, if already set in the environment, else use the default
log_location = os.environ.get("BLUESKY_LOGS", LOG_FOLDER)
# Create the log directory if it doesn't already exist
os.makedirs(log_location, exist_ok=True)

filepath = Path(__file__).resolve().parent
# disable_existing_loggers ensures all loggers have same configuration as below
logging.config.fileConfig(os.path.join(filepath, "logging.conf"), disable_existing_loggers=False)

blueskylogger = logging.getLogger("blueskycore")
