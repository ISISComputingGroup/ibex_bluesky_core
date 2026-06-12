# Custom callbacks ({py:obj}`~ibex_bluesky_core.callbacks.CustomCallback`)

Occasionally, it may be useful to define a custom callback to run after a scan finishes,
which may process the data in some scan-specific or technique-specific way.
{py:obj}`~ibex_bluesky_core.callbacks.CustomCallback` implements a helper for running a
function on the data from a scan after the scan finishes for scalar {math}`x` and {math}`y` data.

As an example, {py:obj}`~ibex_bluesky_core.callbacks.CustomCallback` can be used to calculate
the mean {math}`x` and {math}`y` positions during a scan:

```python
from ibex_bluesky_core.callbacks import CustomCallback
import bluesky.preprocessors as bpp
import bluesky.plans as bp
import numpy as np
import numpy.typing as npt


# Signals for x, y and y_err
x = ...
y = ...
y_err = ...

def calculate_mean(
    x: npt.NDArray[np.float64],
    y: npt.NDArray[np.float64],
    y_err: npt.NDArray[np.float64] | None,
) -> tuple[float, float]:
    # Could be any user-defined logic operating on numpy arrays of x, y and y_err data
    return x.mean(), y.mean()

def plan():
    custom_callback = CustomCallback(
        func=calculate_mean,
        x=x.name,
        y=y.name,
        y_err=y_err.name,
    )

    @bpp.subs_decorator([custom_callback])
    def _inner():
        yield from bp.count([x, y, y_err])
        
    yield from _inner()
    average_x, average_y = custom_callback.result
```