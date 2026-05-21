# First-time setup

This guide is for setting up basic bluesky scans on an instrument for the first time.

## Create bluesky plans & devices areas

Instrument-specific bluesky plans and devices are created under the `inst.bluesky.plans` and `inst.bluesky.devices`
modules, in `c:\Instrument\Settings\config\<instrument>\Python\inst\bluesky`.

## The `devices` module

The devices module should contain {py:obj}`ophyd_async` device objects for devices that may be involved in a scan.
It may also include one or more {py:obj}`ibex_bluesky_core.devices.simpledae.SimpleDae` instances, for data-collection
in different modes.

Devices do not _need_ to be statically defined here; if it is more convenient, devices can be defined on-the-fly in a
plan.

:::{note}
Why do we need {py:obj}`ophyd_async` devices at all? Why can't scans just use string block names?

A string block name does not provide enough information to know when a set is "complete", and therefore when data
collection can start. Different devices may each have a very different "definition of done", or may require
device-specific setting logic.

By defining this device-specific behaviour in an {py:obj}`ophyd_async` _device_, we allow bluesky _plans_ to
operate on _any_ device, without knowing details of the underlying behaviour. {py:obj}`ibex_bluesky_core` provides
utility constructors for common devices, such as {py:obj}`~ibex_bluesky_core.devices.block.block_rw`.
:::

An example `devices` module is:

```python
from ibex_bluesky_core.devices.block import block_r, block_rw, BlockWriteConfig

# Configure a read-write block, whose moves will be "complete" when setpoint and actual
# are equal to within a tolerance.
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

## The `plans` module

The `plans` module contains instrument-specific bluesky plans. These plans may be used to provide a simple interface
for a specific type of scan, or to implement complex plan sequences (such as for
reflectometry auto-alignment procedures).

In either case, these plans may expose whatever interface is convenient or preferred for a given instrument. This gives
each instrument the flexibility to ensure their users are not presented with confusing command line arguments.

The plans in this module will generally do setup, configuration and sequencing logic between multiple plans, and then
delegate to scanning routines built into {py:obj}`bluesky` or {py:obj}`ibex_bluesky_core`.

We'll use aligning an imaginary sample changer, using a diode block readback as an example:

```python
from inst.devices import sample_changer, diode_readback
from ophyd_async.plan_stubs import ensure_connected
import bluesky.plans as bp
import bluesky.plan_stubs as bps
from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.fitting import Gaussian


def sample_changer_scan(full_range=30):
    """
    Optimise the sample changer position by fitting a Gaussian to the readback position of a diode,
    and moving the sample changer to the optimum value.
    
    The scan is a relative scan around the current position, with the specified total scan range.
    """
    yield from ensure_connected(sample_changer, diode_readback)
    
    # ISISCallbacks is a helper for a typical set of 'simple' callbacks
    # (plotting, fitting, live feedback, file-writing),
    # for scans with one independent and one dependent variable.
    icc = ISISCallbacks(
        x=sample_changer.name,
        y=diode_readback.name,
        fit=Gaussian().fit(),
    )
    
    @icc
    def _inner():
        yield from bp.rel_scan([diode_readback], sample_changer, -full_range/2, full_range/2, num=21)
    
    yield from _inner()
    # Move to the optimum value
    yield from bps.mv(sample_changer, icc.live_fit.result.values["x0"])
```

If you wish for these plans to be available to users by default in a scripting console, add the imports to `inst/init_<inst_name>.py`. Once you have done this, users will be able to run:

```python
RE(sample_changer_scan())
RE(sample_changer_scan(50))
```

In the IBEX scripting console. In this example, this command will leave the sample changer aligned in its optimum
position, along with displaying plots, live feedback, and saving files.

Notice that this plan is "opinionated"; it does not provide a user with all possible options, but a minimal
beamline-specific interface with sensible defaults.

### Integrating bluesky plans with existing scripts

{py:obj}`bluesky` plans are primarily _designed_ to be executed interactively, by a user at a Python shell.

To integrate a bluesky plan with an existing script, use the {py:obj}`ibex_bluesky_core.run_engine.run_plan` function:

```python
from genie_python import genie as g
from inst.bluesky.plans import sample_changer_scan
from ibex_bluesky_core.run_engine import run_plan


def acquire_data():
    # An existing acquisition sequence...
    g.begin()
    g.waitfor_uamps(10)
    g.end()
    
    # Realign our imaginary sample changer using a bluesky scan...
    run_plan(sample_chager_scan())
    
    # Another existing acquisition sequence...
    g.begin()
    g.waitfor_uamps(10)
    g.end()
```

:::{seealso}
See the documentation of {py:obj}`ibex_bluesky_core.run_engine.run_plan` for further details.
:::
