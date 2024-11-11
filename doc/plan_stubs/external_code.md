# `call_sync` (calling external code)

API reference: {py:obj}`ibex_bluesky_core.plan_stubs.call_sync`

All interaction with the "outside world" should be via bluesky messages, and **not** directly called from
within a plan. For example, the following is **bad**:

```python
import bluesky.plan_stubs as bps
from genie_python import genie as g

def bad_plan():
    yield from bps.open_run()
    g.cset("foo", 123)  # This is bad - must not do this
    yield from bps.close_run()
```

```{danger}
External I/O - including most `genie_python` or `inst` functions -  should never be done directly in a plan,
as it will break:
- Rewindability (for example, the ability to interrupt a scan and then later seamlessly continue it)
- Simulation (the `cset` above would be executed during a simulation)
- Error handling (including ctrl-c handling)
- Ability to emit documents
- Ability to use bluesky signals
- ...
```

In the above case, a good plan, which uses bluesky messages in a better way using 
a bluesky-native `Block` object, would be:

```python
import bluesky.plan_stubs as bps
from ophyd_async.plan_stubs import ensure_connected
from ibex_bluesky_core.devices.block import block_rw

foo = block_rw(float, "foo")

def good_plan():
    yield from ensure_connected(foo)
    yield from bps.open_run()
    yield from bps.mv(foo, 123)
    yield from bps.close_run()
```

However, if the functionality you want to use is not yet natively available in bluesky, a fallback option
for synchronous functions is available using the `call_sync` plan stub:

```python
import bluesky.plan_stubs as bps
from ibex_bluesky_core.plan_stubs import call_sync
from genie_python import genie as g

def good_plan():
    yield from bps.open_run()
    
    # Note use of g.some_function, rather than g.some_function() - i.e. a function reference
    # We can also access the returned value from the call.
    return_value = yield from call_sync(g.some_function, 123, keyword_argument=456)
    yield from bps.checkpoint()
    yield from bps.close_run()
```

It is strongly recommended that any functions run in this way are "fast" (i.e. less than a few seconds).
In particular, avoid doing arbitrarily-long waits - for example, waiting for detector data
or sample environment. For these long-running tasks, seek to implement at least the long-running parts using 
native bluesky mechanisms.

```{note}
`bps.checkpoint()` above instructs bluesky that this is a safe point from which to resume a plan. 
`call_sync` always clears an active checkpoint first, as the code it runs may have arbitrary external
side effects.

If a plan is interrupted with no checkpoint active, it cannot be resumed later (it effectively forces
the plan to abort rather than pause). You will see `bluesky.utils.FailedPause` as part of the traceback
on ctrl-c, if this is the case.
```
