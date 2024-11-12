# Logging
To invoke the `ibex_bluesky_core` logger, create and use a `logger` object in [the standard way](https://docs.python.org/3/library/logging.html):

```python
import logging
logger = logging.getLogger(__name__)
logger.warning("Message to be logged")
```

The logger utilizes a `TimedRotatingFileHandler` defined in `src/ibex_bluesky_core/log.py` that rolls over the log at midnight.

By default, the log files will be created in `c:\instrument\var\logs\bluesky`. This can be configured by setting
the `IBEX_BLUESKY_CORE_LOGS` environment variable.

There are 3 primary logger objects which are "interesting" in the context of `ibex_bluesky_core`:
- `ibex_bluesky_core` itself
- `bluesky`, for low-level diagnostic logging from the run engine & plans
- `ophyd_async` for low-level diagnostic logging from ophyd-async devices

The default logging level for bluesky libraries is defined at `INFO`. This means that events of lesser severity will not be logged. 
To change the logging level for all bluesky libraries simultaneously, call: 

```python
from ibex_bluesky_core.log import set_bluesky_log_levels
set_bluesky_log_levels("DEBUG")
```

To change the logging level of just a single library (for example, just `opyhyd_async`), use the standard
python `logging` mechanisms:

```python
import logging
logging.getLogger("ophyd_async").setLevel("DEBUG")
```
