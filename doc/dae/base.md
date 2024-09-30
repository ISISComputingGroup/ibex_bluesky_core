# DaeBase (base class)

`Dae` is the principal class in ibex_bluesky_core which exposes configuration settings
and controls from the ISIS data acquisition electronics (DAE).

> **_ℹ️_**  
> The `Dae` class is not intended to be used directly in scans - it is a low-level class
> which directly exposes functionality from the DAE, but has no scanning functionality by
> itself.
> 
> It is intended that this object is only used directly when:
> - Configuring DAE settings within a plan.
> - For advanced use-cases, if arbitrary DAE control is required from a plan - but note 
>   that it will usually be better to implement functionality at the device level rather 
>   than the plan level.
> 
> For other use-cases, a user-facing DAE class is likely to be more appropriate to use
> as a detector in a scan - this class cannot be used by itself.

# Top-level signals

Some DAE parameters, particularly metadata parameters, are exposed as simple signals, 
for example `dae.title` or `dae.good_uah`.

These signals are directly readable and settable from plans:

```python
import bluesky.plan_stubs as bps
from ibex_bluesky_core.devices.dae.dae import Dae

def plan(dae: Dae):
    current_title = yield from bps.rd(dae.title)
    yield from bps.mv(dae.title, "new title")
```

# Period-specific signals

For signals which apply to the current period, see `dae.period`, which contains signals
such as `dae.period.good_uah` (the number of good uamp-hours collected in the current period).
