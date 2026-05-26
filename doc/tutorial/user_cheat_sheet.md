# User cheat-sheet

This guide is targeted at a beamline user or instrument scientist wanting to *run* scans, either interactively or from a user python script.

## Running a scan

:::{note}
This guide assumes that the scan you want to run is either a {doc}`general plan </plans/plans>`, or has
already been defined by an instrument scientist as an instrument-specific scan.

To find out which instrument-specific scans are available on your beamline, consult the beamline instrument
scientist or the beamline manual if available.
:::

In this example, we will run a {py:obj}`~ibex_bluesky_core.plans.motor_scan`. This is a {doc}`generic plan </plans/plans>` provided by the {py:obj}`ibex_bluesky_core` library, which performs a one-dimensional step-scan
of a motor block against monitor-normalised intensity, {math}`I/I_0`, from one or more detector pixels. We'll then fit
a {ref}`fit_gaussian` to the resulting curve and extract the centre (`x0`) of the fit.

::::{tab-set}
:sync-group: call-from

:::{tab-item} Run interactively
:sync: interactive

To run a bluesky plan interactively, use the `RE` object which is automatically created by the IBEX scripting console:

```python
# Note: imports may have been done automatically in `init_<instrument>.py` for your instrument.
from ibex_bluesky_core.plans import motor_scan
from ibex_bluesky_core.fitting import Gaussian


result = RE(motor_scan(
    "motor_block", 
    start=5, 
    stop=15, 
    num=11, 
    model=Gaussian().fit(), 
    frames=100, 
    det=10, 
    mon=1
))
print(result.plan_result.live_fit.result.values["x0"])
```
:::

:::{tab-item} Call from a script
:sync: script

To run a bluesky plan non-interactively, use {py:obj}`ibex_bluesky_core.run_engine.run_plan`:

```python
from ibex_bluesky_core.plans import motor_scan
from ibex_bluesky_core.run_engine import run_plan
from ibex_bluesky_core.fitting import Gaussian


def an_external_script_function():
    result = run_plan(motor_scan(
        "motor_block",
        start=5,
        stop=15,
        num=11,
        model=Gaussian().fit(),
        frames=100,
        det=10,
        mon=1
    ))
    print(result.plan_result.live_fit.result.values["x0"])
```
:::
::::

Plans provided in the {py:obj}`ibex_bluesky_core.plans` module have reference documentation describing their
arguments and return values (for example, click on {py:obj}`~ibex_bluesky_core.plans.motor_scan`).
For documentation on instrument-specific plans (under the `inst.bluesky.plans` module), consult the
instrument scientist or beamline manual for your instrument.
