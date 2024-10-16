# Bluesky logger

To invoke the bluesky logger, import as `from ibex_bluesky_core.logger import logger` and use it at the desired level:
`logger.blueskylogger.warning("Message to be logged")`
The logger utilizes a `TimedRotatingFileHandler` defined in the `logging.conf` file that rolls over the log at midnight.

The default logging level is defined at `INFO`.
