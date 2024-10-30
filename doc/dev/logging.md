# Logging

To invoke the bluesky logger, import and use it at the desired level:
```python
from ibex_bluesky_core.logger import logger
logger.blueskylogger.warning("Message to be logged")
```
The logger utilizes a `TimedRotatingFileHandler` defined in the `logging.conf` file that rolls over the log at midnight.

The default logging level is defined at `INFO`. This means that events of lesser severity will not be logged. To change the default level, change level attribute of logger_blueskycore in the `logging.conf`
