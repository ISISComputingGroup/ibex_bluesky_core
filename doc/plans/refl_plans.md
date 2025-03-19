# Reflectometry Plans

For reflectometers- we provide a few generic plans which can be used to align beamlines.

## Full-Auto Alignment Plan

The {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.optimise_axis_against_intensity` plan is designed to scan over a movable against beam intensity, and given which fitting parameter is chosen to be optimised and the fitting method, it will aim to find an optimum value. See [`standard fits`](../fitting/standard_fits.md) for the fitting parameters for each fitting model you can use. At this stage it will check if the value is 'sensible'- there are some default checks but the user is encouraged to provide their own checks. If found to be sensible, the motor will be moved to this value, otherwise it will optionally run a callback that can be provided, and then ask the user if they want to rescan or conttinue to move the movable.

The idea for how we expect the main auto-alignment plan to be used is that at the top / instrument level, you will move all other movables to some position ready to align, yield from this plan and then re-zero the motor.
The following is how you would do this for a reflectometry parameter as your movable:

```python

def full_autoalign_plan() -> Generator[Msg, None, None]:
 
    count = 10
    det_pixels = centred_pixel(DEFAULT_DET, PIXEL_RANGE)
    dae = monitor_normalising_dae(
        det_pixels=det_pixels,
        frames=FRAMES,
        periods=PERIODS,
        save_run=SAVE_RUN,
        monitor=DEFAULT_MON,
    )

    s1vg = ReflParameter(prefix=PREFIX, name="S1VG", changing_timeout_s=60)
    # Interfaces with the reflectometry server

    yield from bps.mv(dae.number_of_periods, count)

    yield from ensure_connected(s1vg, dae)

    print("Starting auto-alignment...")

    # S1VG

    yield from bps.mv(s1vg, -0.1)
    yield from autoalign_utils.optimise_axis_against_intensity(
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

As mentioned prior, it is recommended that for each movable you want to align, you should provide a checking function, to make sure that for the value you receive for the chosen fitting paramater e.g centre of a gaussian, is sensible. If the optimised value is not found to be sensible then you will have the option to either type 1 and restart the alignment for this movable, or press 2 and continue with moving the movable to the found value. The following is how you would make a check function with the right signature and pass it to {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.optimise_axis_against_intensity`:

```python

def s1vg_checks(result: ModelResult, alignment_param_value: float) -> bool: # Must take a ModelResult and a float
    """Check for optimised S1VG value. Returns True if sensible."""
    rsquared_confidence = 0.9
    expected_param_value = 1.0
    expected_param_value_tol = 0.1
    max_peak_factor = 5.0

    # Check that r-squared is above a tolerance
    if result.rsquared < rsquared_confidence:
        return False

    # For S1VG, provide a value you would expect for it,
    # assert if its not close by a provided factor
    if not isclose(expected_param_value, alignment_param_value, abs_tol=expected_param_value_tol):
        return False

    # Is the peak above the background by some factor (optional because param may not be for
    # a peak, or background may not be a parameter in the model).
    if result.values["background"] / result.model.func(alignment_param_value) <= max_peak_factor:
        return False

    return True

# ...

yield from autoalign_utils.optimise_axis_against_intensity(
        dae=dae,
        alignment_param=s1vg,
        fit_method=SlitScan.fit(),
        fit_param="inflection0",
        rel_scan_ranges=[0.3, 0.05], # Scan with range of 0.3, then 0.05
        num_points=10,
        is_good_fit=s1vg_checks # Pass s1vg_checks
    )

```

Note that {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.optimise_axis_against_intensity` also has parameters:

`periods` - Whether to use periods.

`save_run` - Whether to save runs.

`problem_found_plan` - A callback plan for if the optimised value is not found to be sensible.

To define a `problem_found_plan` you must use the following function signature:

```python

def s1vg_problem() -> Generator[Msg, None, None]:
    # ...
    yield from ...

```
