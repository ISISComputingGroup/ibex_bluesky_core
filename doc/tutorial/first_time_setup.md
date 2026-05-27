# First-time setup guide

This guide is for setting up (defining) **basic** bluesky scans on an instrument.

If you need help or advice on writing new bluesky plans for an instrument, please
{external+ibex_user_manual:ref}`contact the Experiment Controls team <report_a_problem>`.

## Create bluesky plans & devices areas

Instrument-specific bluesky plans and devices are created under the `inst.bluesky.plans` and `inst.bluesky.devices`
modules, in `c:\Instrument\Settings\config\<instrument>\Python\inst\bluesky`.

Beamlines may wish to provide a short alias for all their bluesky functionality; some beamlines use namespaces
like `pb` (short for POLREF bluesky) for this purpose. This helps users find relevant objects using autocomplete. 
For example:

```python
# c:\Instrument\Settings\config\<instrument>\Python\init_<instrument>.py

import inst.bluesky as pb
```

## The `devices` module

:::{note}
**What is a device?**

Device objects encapsulate the details of how some specific device is controlled, reading or writing to EPICS PVs.
Each device object may contain logic including:
- Which data can be read back from this hardware.
- How to acquire a new reading; this may range from a simple PV read, through to specialised data reductions on DAE data.
- How to set a device to a new value; this may range from a simple PV write, through to more complex sequences required to drive a specific device. This also includes detecting when a "set" has completed.
- How to set up hardware before and after a whole scan.

{py:obj}`ibex_bluesky_core` provides utility constructors for common devices, such as {py:obj}`~ibex_bluesky_core.devices.block.block_rw`. See the {py:obj}`ibex_bluesky_core.devices` module for specialised device classes provided by {py:obj}`ibex_bluesky_core`.
:::

The devices module should contain {py:obj}`ophyd_async` device objects for devices that may be involved in a scan, for
example common {doc}`/devices/blocks` involved in scans.
It may also include one or more {py:obj}`~ibex_bluesky_core.devices.simpledae.SimpleDae` instances, for data-collection in different modes.

Devices do not _need_ to be statically defined here; if it is more convenient, device objects can be defined on-the-fly during the execution of a plan.

An example `devices` module is:

:::{dropdown} Click to expand example devices module
```python
from ibex_bluesky_core.devices.block import block_r, block_rw, BlockWriteConfig
from ibex_bluesky_core.devices.reflectometry import refl_parameter
from ibex_bluesky_core.devices.simpledae import monitor_normalising_dae
from ibex_bluesky_core.utils import centred_pixel
from ophyd_async.epics.core import epics_signal_rw

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

# A read-write epics PV (not a block). A set will be marked as "complete" as soon as
# the value is written to the device, which may not be suitable for all devices
timing = epics_signal_rw(float, "IN:INSTNAME:DG645_01:BDelayAO", name="timing")

# A reflectometry parameter - only meaningful on reflectometry beamlines. A set will be marked
# as "complete" once the reflectometry server specifies that this axis' motion is complete.
s1vg = refl_parameter(name="S1VG")

# A convenience DAE object which counts using a common configuration.
# Note: it is often more flexible to dynamically create DAE objects during a plan, if parameters may vary
# each time the scan is invoked.
autoalign_dae = monitor_normalising_dae(
    det_pixels=centred_pixel(20, pixel_range=10),
    frames=200,
    periods=False,
    save_run=False,
    monitor=2,
)
```
:::

## The `plans` module

:::{note}
**What is a plan?**

A "plan" is a sequence of bluesky instructions (for example, move a motor or count from a detector), which are combined to make scanning routines. Plans are almost always written as [python generator functions](https://wiki.python.org/moin/Generators), using Python's `yield` and `yield from` syntax.
:::

The `plans` module contains instrument-specific bluesky plans. These plans may range from simple beamline-specific
interfaces for a specific type of scan, to complex plan sequences incorporating multiple scans (such as
reflectometry auto-alignment procedures).

In either case, these plans may expose whatever interface is convenient or preferred for a given instrument. This gives
each instrument the flexibility to ensure their users are not presented with confusing command line arguments, that
defaults 'make sense', but equally that enough flexibility is provided for common beamline use-cases.

We'll use aligning an imaginary sample changer, using a diode block readback as an example:

:::{dropdown} Click to expand `sample_changer_scan` plan
```python
from inst.devices import sample_changer, diode_readback  # Define these devices in the "devices" module
from ophyd_async.plan_stubs import ensure_connected
import bluesky.plans as bp
import bluesky.plan_stubs as bps
from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.fitting import Gaussian


def sample_changer_scan(full_range=30):
    """
    Optimise the sample changer position by fitting a Gaussian to the readback position of a diode,
    and moving the sample changer to the optimum value.
    
    The scan is a relative scan around the current position, with a user-specified total scan range.
    """
    # Bluesky connects devices up-front for efficiency, and so that plans fail-fast if a
    # required PV is not available.
    yield from ensure_connected(sample_changer, diode_readback)
    
    # ISISCallbacks is a helper for a typical set of 'simple' callbacks
    # (plotting, fitting, live feedback, file-writing),
    # for scans with one independent and one dependent variable.
    #
    # More complex arrangements are possible, but beyond the scope of this introductory tutorial.
    icc = ISISCallbacks(
        x=sample_changer.name,
        y=diode_readback.name,
        fit=Gaussian().fit(),
    )
    
    # Apply the callbacks defined above to a "scan" command.
    @icc
    def _inner():
        # We delegate to bluesky's built-in relative scan command.
        yield from bp.rel_scan([diode_readback], sample_changer, -full_range/2, full_range/2, num=21)

    yield from _inner()

    if icc.live_fit.result is not None:
        # Move to the optimum value
        yield from bps.mv(sample_changer, icc.live_fit.result.values["x0"])
    else:
        pass  # Handling for case where the fit failed
```
:::

Assuming that the imports were added to `init_<instrument>.py`, for example using the `pb` alias, a user can now run
in the IBEX scripting console:

```python
RE(pb.sample_changer_scan())
# ... or
RE(pb.sample_changer_scan(50))
```

The `RE` object, the {ref}`bluesky run engine <concept_run_engine>`, is available by default in the IBEX scripting console. It is used to interactively execute any bluesky plan.

In this example, this command will leave the sample changer aligned in its optimum
position, along with displaying plots, live feedback, and saving files.

Notice that this plan is "opinionated"; it does not provide a user with all possible options, but a minimal,
beamline-specific interface with sensible defaults. In this case, the plan was highly specific (it only works
for a sample changer).

Suppose we now want a different plan: we still want to align an axis, but now we want:
- To count using the DAE, rather than a diode block.
- For the user to be able to specify which axis to scan.
- We'd like an absolute scan rather than a relative scan.

:::{dropdown} Click to expand `detector_scan` plan
```python
from ophyd_async.plan_stubs import ensure_connected
from bluesky.protocols import NamedMovable
import bluesky.plans as bp
import bluesky.plan_stubs as bps
from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.fitting import Gaussian
from ibex_bluesky_core.devices.simpledae import monitor_normalising_dae
from ibex_bluesky_core.utils import centred_pixel
from ibex_bluesky_core.plan_stubs import with_num_periods

def detector_scan(block: NamedMovable, start, stop, num, frames=200):
    """
    Optimise the position of a block by fitting a Gaussian to the intensity on the detector,
    and moving the block to the optimum value.
    """
    dae = monitor_normalising_dae(
        det_pixels=centred_pixel(20, pixel_range=10),
        frames=frames,
        periods=True,
        save_run=False,
        monitor=2,
    )
    
    # Bluesky connects devices up-front for efficiency, and so that plans fail-fast if a
    # required PV is not available.
    yield from ensure_connected(block, dae)

    # When read, the DAE _may_ provide multiple readbacks per scan point.
    # Here, we tell bluesky to use the normalised intensity as the dependent variable,
    # and the corresponding standard deviations in plotting and fitting functions.
    icc = ISISCallbacks(
        x=block.name,
        y=dae.reducer.intensity.name,
        yerr=dae.reducer.intensity_stddev.name,
        fit=Gaussian().fit(),
    )
    
    # Apply the callbacks defined above to a "scan" command.
    @icc
    def _inner():
        # We delegate to bluesky's built-in absolute scan command.
        yield from bp.scan([dae], block, start, stop, num)

    # This ensures that the DAE is configured with sufficient DAE periods before the scan,
    # and then puts the number of DAE periods back to what it was before after the scan
    # (including if the scan failed with an exception).
    yield from with_num_periods(_inner(), dae=dae, number_of_periods=num)

    if icc.live_fit.result is not None:
        # Move to the optimum value
        yield from bps.mv(block, icc.live_fit.result.values["x0"])
    else:
        pass  # Handling for case where the fit failed
```
:::

Now our users would call the plan as:

```python
RE(pb.detector_scan(pb.sample_changer, 30, 50, 11))
```

If a plan is useful and generic enough to apply to multiple beamlines, please
{external+ibex_user_manual:ref}`get in touch with the IBEX team <report_a_problem>` and we can add the relevant plan
to a general or technique-specific area of {py:obj}`ibex_bluesky_core`.

## Integrating bluesky plans with existing scripts

The {py:obj}`bluesky` `RE` object is primarily _designed_ to be executed interactively, by a user at a Python shell.

To integrate a bluesky plan with an existing script, use the {py:obj}`ibex_bluesky_core.run_engine.run_plan` function
instead:

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
