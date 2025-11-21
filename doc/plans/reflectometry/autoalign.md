# Auto-alignment

For reflectometers, we provide a few generic plans which can be used as helpers for automated beamline alignment.

The {py:obj}`~ibex_bluesky_core.plans.reflectometry.optimise_axis_against_intensity` plan is designed to scan a {py:obj}`~bluesky.protocols.Movable` against beam intensity, and given a fitting routine, will aim to find an optimum value. [Standard fits](/callbacks/fitting/standard_fits.md) have been implemented and can be used easily, or custom fits can also be used.

Once a fit has been performed, {py:obj}`~ibex_bluesky_core.plans.reflectometry.optimise_axis_against_intensity` will check that the fit parameters are 'sensible' - there are some default checks, but the user is encouraged to provide their own checks. If the checks pass, the motor will be moved to the fit value, otherwise it will run a user-provided callback, and then ask the user if they want to rescan or move anyway.

Reflectometer auto-alignment routines will generally be structured as a series of calls which:
- Put the beamline into a suitable state for the alignment
- Call {py:obj}`~ibex_bluesky_core.plans.reflectometry.optimise_axis_against_intensity` to optimise the axis. This will leave the axis parked at its optimal position.
- Redefine that position as zero (note: this is fully optional, but common on reflectometers)
- Repeat the above steps for subsequent axes

For example, using a reflectometry parameter as your {py:obj}`~bluesky.protocols.Movable`:

```python
def full_autoalign_plan() -> Generator[Msg, None, None]:
 
    det_pixels = centred_pixel(DEFAULT_DET, PIXEL_RANGE)
    dae = monitor_normalising_dae(
        det_pixels=det_pixels,
        frames=FRAMES,
        periods=PERIODS,
        save_run=SAVE_RUN,
        monitor=DEFAULT_MON,
    )

    # Interfaces with the reflectometry server
    s1vg = ReflParameter(prefix=PREFIX, name="S1VG", changing_timeout_s=60)

    yield from ensure_connected(s1vg, dae)

    print("Starting auto-alignment...")

    # S1VG

    yield from bps.mv(s1vg, -0.1)
    yield from optimise_axis_against_intensity(
        dae=dae,
        alignment_param=s1vg,
        fit_method=SlitScan.fit(), # What form of data do you expect
        fit_param="inflection0", # Which fitting paramater do you want to optimise
        rel_scan_ranges=[0.3, 0.05], # Scan with range of 0.3, then 0.05
        num_points=10, # Number of points in a scan.
    )
    yield from bps.mv(s1vg.redefine, 0.0)  # Redefine current motor position to be 0

    # Other params
    # ....

    print("Auto alignment complete.")
```

As mentioned prior, it is recommended that for each {py:obj}`~bluesky.protocols.Movable` to be aligned, you should provide a checking function, to make sure that for the value you receive for the chosen fitting paramater e.g centre of a gaussian, is physically reasonable. If the optimised value fails the check, then you will have the option to either restart the alignment for this axis, or continue moving this axis to the located value despite the failing check.

The following is how you would define a check function and pass it to {py:obj}`~ibex_bluesky_core.plans.reflectometry.optimise_axis_against_intensity`:

```python
from lmfit.model import ModelResult
from math import isclose


def s1vg_checks(result: ModelResult, alignment_param_value: float) -> str | None: # Must take a ModelResult and a float
    """Check for optimised S1VG value. Returns True if sensible."""
    rsquared_confidence = 0.9
    expected_param_value = 1.0
    expected_param_value_tol = 0.1
    max_peak_factor = 5.0

    # Check that r-squared is above a tolerance
    if result.rsquared < rsquared_confidence:
        return "R-squared below confidence level."

    # For S1VG, provide a value you would expect for it,
    # assert if its not close by a provided factor
    if not isclose(expected_param_value, alignment_param_value, abs_tol=expected_param_value_tol):
        return "Optimised value is not close to expected value."

    # Is the peak above the background by some factor (optional because param may not be for
    # a peak, or background may not be a parameter in the model).
    if result.values["background"] / result.model.func(alignment_param_value) <= max_peak_factor:
        return "Peak was not above the background by factor."
    
    # Everything is fine, so return None
    return None

# ...

def plan():
    yield from optimise_axis_against_intensity(
        dae=dae,
        alignment_param=s1vg,
        fit_method=SlitScan.fit(),
        fit_param="inflection0",
        rel_scan_ranges=[0.3, 0.05], # Scan with range of 0.3, then 0.05
        num_points=10,
        is_good_fit=s1vg_checks # Pass s1vg_checks
    )

```

To determine what to do in the event of a value being "invalid" you can use a plan like so:

```python
from ibex_bluesky_core.plans.reflectometry import optimise_axis_against_intensity
from ibex_bluesky_core.fitting import SlitScan
from typing import Generator
from bluesky.utils import Msg
import bluesky.plan_stubs as bps


def problem_found_plan() -> Generator[Msg, None, None]:
    # This must be a plan, if it doesn't otherwise yield, make it a plan
    # by yielding from bps.null()
    yield from bps.null()
    print("There was a problem - oh no!")


def plan():
    yield from optimise_axis_against_intensity(
        dae=dae,
        alignment_param=s1vg,
        fit_method=SlitScan.fit(),
        fit_param="inflection0",
        rel_scan_ranges=[0.1],
        num_points=1,  # Fit will never converge with just 1 point which should cause a "problem".
        problem_found_plan=problem_found_plan
    )
```
