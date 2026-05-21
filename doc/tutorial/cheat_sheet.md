# Bluesky plan cheat-sheet

## Absolute scan of a motor block against the DAE

This scan uses a {doc}`general plan </plans/plans>`, {py:obj}`ibex_bluesky_core.plans.motor_scan`, to scan a motor
block specified as a string, against a DAE spectrum normalised by a monitor spectrum.

The specified block can be any block which causes an IBEX motor to move. Movement is assumed to be complete using
the same mechanism as {external+genie_python:py:obj}`genie.waitfor_move`.

::::{tab-set}
:sync-group: call-from

:::{tab-item} Run interactively
:sync: interactive

```python
# Note: imports can be automatically done by init_<instrument>.py
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

:::{tab-item} Call from an outer bluesky plan
:sync: plan

```python
from typing import Generator
from bluesky import Msg
from ibex_bluesky_core.plans import motor_scan
from ibex_bluesky_core.fitting import Gaussian


def outer_plan() -> Generator[Msg, None, None]:
    result = yield from motor_scan(
        "motor_block", 
        start=5, 
        stop=15, 
        num=11, 
        model=Gaussian().fit(), 
        frames=100, 
        det=10, 
        mon=1
    )
    print(result.live_fit.result.values["x0"])
```
:::

:::{tab-item} Call from an external script
:sync: script

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


## Scan one block against another block

This scan uses the bluesky-native {external+bluesky:py:obj}`bluesky.plans.scan` plan, along with two block definitions,
to scan one block against another.

The example below assumes that two blocks have been defined in `inst.bluesky.devices`:

```python
from ibex_bluesky_core.devices.block import block_r, block_rw, BlockWriteConfig

# Configure a read-write block, whose moves will be "complete" when setpoint and actual values
# are equal to within a specified tolerance.
motor_block = block_rw(
    float, 
    "motor_block",
    write_config=BlockWriteConfig(
        set_success_func=lambda setpoint, actual: abs(setpoint-actual) < 0.1
    ),
)

# Configure a read-only block
readback_block = block_r(
    float,
    "readback_block",
)
```

If we want to allow the users to scan two arbitrary blocks against each other, we could define a _basic_ arbitrary block-block scan in the `inst.bluesky.plans` module:

```python
from typing import Generator
from ibex_bluesky_core.devices.block import BlockR, BlockRw
from ibex_bluesky_core.fitting import FitMethod
from ibex_bluesky_core.callbacks import ISISCallbacks
from ophyd_async.plan_stubs import ensure_connected
from bluesky import Msg
import bluesky.plans as bp


def bbscan(
    x: BlockRw[float],
    y: BlockR[float],
    start: float,
    stop: float,
    num: int,
    fit: FitMethod | None = None,
) -> Generator[Msg, None, ISISCallbacks]:
    """
    Optimise the sample changer position by fitting a Gaussian to the readback position of a diode,
    and moving the sample changer to the optimum value.

    The scan is a relative scan around the current position, with the specified total scan range.
    """
    yield from ensure_connected(x, y)

    # ISISCallbacks is a helper for a typical set of 'simple' callbacks
    # (plotting, fitting, live feedback, file-writing),
    # for scans with one independent and one dependent variable.
    icc = ISISCallbacks(
        x=x.name,
        y=y.name,
        fit=fit,
    )

    @icc
    def _inner():
        yield from bp.scan([y], x, start, stop, num)

    yield from _inner()
    return icc
```

Note that in this example, `bbscan` makes assumptions which are not _generally_ true of every possible block-block scan, including:
- That we will only have one `x` and `y` variable, and one corresponding fit
- That we don't have `y` uncertainties
- That we want to do an absolute scan with equal step sizes

::::{tab-set}
:sync-group: call-from

:::{tab-item} Run interactively
:sync: interactive

```python
# Note: imports can be automatically done by init_<instrument>.py
from inst.bluesky.devices import motor_block, readback_block
from inst.bluesky.plans import bbscan
from ibex_bluesky_core.fitting import Gaussian


result = RE(bbscan(
    x=motor_block,
    y=readback_block,
    start=10,
    stop=20,
    num=11,
    fit=Gaussian().fit(),
))
print(result.plan_result.live_fit.result.values["x0"])
```
:::

:::{tab-item} Call from an outer bluesky plan
:sync: plan

```python
from typing import Generator
from bluesky import Msg
from inst.bluesky.devices import motor_block, readback_block
from inst.bluesky.plans import bbscan
from ibex_bluesky_core.fitting import Gaussian


def outer_plan() -> Generator[Msg, None, None]:
    result = yield from bbscan(
        x=motor_block,
        y=readback_block,
        start=10,
        stop=20,
        num=11,
        fit=Gaussian().fit(),
    )
    print(result.live_fit.result.values["x0"])
```
:::

:::{tab-item} Call from an external script
:sync: script

```python
from inst.bluesky.devices import motor_block, readback_block
from inst.bluesky.plans import bbscan
from ibex_bluesky_core.fitting import Gaussian
from ibex_bluesky_core.run_engine import run_plan


def an_external_script_function():
    result = run_plan(bbscan(
        x=motor_block,
        y=readback_block,
        start=10,
        stop=20,
        num=11,
        fit=Gaussian().fit(),
    ))
    print(result.plan_result.live_fit.result.values["x0"])
```
:::
::::
