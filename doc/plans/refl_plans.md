# Reflectometry Plans

For reflectometers- we provide a few generic plans which can be used to align beamlines.

## [AlignmentParam](ibex_bluesky_core.plans.reflectometry.autoalign_utils.AlignmentParam)

A {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.AlignmentParam` represents a device on your beamline that needs to be optimised against the intensity of the beam. It is a wrapper around ReflParameter, of which is used to be able to move the device. To instantiate a {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.AlignmentParam` you should do the following as a minimum-

```python
... # Other imports
from ibex_bluesky_core.plans.reflectometry.autoalign_utils import AlignmentParam

my_device = AlignmentParam(
    name="my_device",
    rel_scan_ranges=[2.0],
    fit_method=Gaussian().fit(),
    fit_param="x0"
    )
```

`name` - Should be the same as the corresponding reflectometry parameter.

`rel_scan_ranges` - This is used for when it comes to scanning over the device. A range represents the distance the device will move, with the current device position at the centre of this. E.g passing `[2.0]` means that the device will be scanned between `device_pos - 1.0` and `device_pos + 1.0`, for a total range of `2.0`. Note that this is a list, so providing more than one scan range will mean that subsequent scans will happen. If you provide multiple scan ranges of decreasing value then this could result in the plan finding a result closer to an optimum.

Note that between scans, the motor is moved to the optimum and position redefined as zero.

`fit_method` - When scanning over the device against beam intensity, what shape of data you would expect to find.

`fit_param` - The fitting parameter you want to optimise when scanning against beam intensity, the property you're interested in. E.g centre of a Gaussian `x0`, see [`standard fits`](../fitting/standard_fits.md) for the fitting parameters for each fitting model you can use.

### Pre-align Parameters

To build on the above, the constructor for {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.AlignmentParam` also has an option for assigning positions to other AlignmentParams, used in the following manner-

```python
... # Other imports
from ibex_bluesky_core.plans.reflectometry.autoalign_utils import AlignmentParam

my_device = AlignmentParam(
    name="my_device",
    rel_scan_ranges=[2.0],
    fit_method=Gaussian().fit(),
    fit_param="x0",
    pre_align_param_positions={"my_device": 1.0, "my_device2": 2.0}
    )
```

`pre_align_param_positions` is a dictionary of {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.AlignmentParam` name to a motor position. So in the above example we expect `"my_device"` to move to `1.0` and `"my_device2"` to move to `2.0`. To perform these moves the [`pre_align_params`](ibex_bluesky_core.plans.reflectometry.autoalign_utils.AlignmentParam.pre_align_params) method can be called.

```python
... # Code from above

my_device2 = AlignmentParam(
    name="my_device2",
    rel_scan_ranges=[1.0],
    fit_method=Gaussian().fit(),
    fit_param="x0"
    )

parameters = [my_device, my_device2]

def pre_align() -> Generator[Msg, None, None]:
    yield from my_device.pre_align_params(parameters)
# This will move my_device to 1.0 and my_device2 to 2.0 simultaneously

```

Note that there is also a `get_movable` method which returns a {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.AlignmentParam`'s underlying `ReflParameter `object.

## Full-Auto Alignment Plan

The {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.optimise_axis_against_intensity` plan by default scans over a motor against beam intensity, and given which fitting parameter chosen to be optimised and the fitting method, it will find aim to find an optimum value. At this stage it will check if the value is 'sensible'- there are some default checks but the user is encouraged to provide their own checks per {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.AlignmentParam` as described in the next section. If found to be sensible, the motor will be moved to this value, and the motor position redefined as 0 at the reflectometry server level.

The idea for how we expect the main auto-alignment plan to be used is that at the top / instrument level, a list of {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.AlignmentParam`s, are to be optimised against the intensity of the beam; whereby the plan is ran once for each element, in the order of the provided list. The following is how you make a simple call to this plan-

```python

my_device = AlignmentParam(
    name="my_device",
    rel_scan_ranges=[2.0],
    fit_method=Gaussian().fit(),
    fit_param="x0",
    )

parameters = [my_device]

def auto_align() -> Generator[Msg, None, None]:

    det_pixels = centred_pixel(DEFAULT_DET, PIXEL_RANGE)
    dae = monitor_normalising_dae(
        det_pixels=det_pixels,
        frames=FRAMES,
        periods=PERIODS,
    )

    yield from bps.mv(dae.number_of_periods, COUNT)  # type: ignore

    yield from ensure_connected(my_device.get_movable(), dae)  # type: ignore

    yield from autoalign_utils.optimise_axis_against_intensity(
        dae=dae,
        alignment_param=my_device
    )

```

It is expected that before each {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.AlignmentParam` is optimised, it would make sense for all motors to be moved to a preset position. This can be done using the `pre_align_params` method of {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.AlignmentParam`; this is called using the list of all {py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.AlignmentParam`s so that they are all moved to some preset position. `pre_align_params` is passed as a parameter to `optimise_axis_against_intensity` as the `pre_align_plan` callback. Also note that there are callbacks for `post_align_plan` and `problem_found_plan`. The following is how this can be done-

```python

my_device = AlignmentParam(
    name="my_device",
    rel_scan_ranges=[2.0],
    fit_method=Gaussian().fit(),
    fit_param="x0",
    pre_align_param_positions={"my_device": 1.0, "my_device2": 2.0}
    )

my_device2 = AlignmentParam(
    name="my_device2",
    rel_scan_ranges=[1.0],
    fit_method=Gaussian().fit(),
    fit_param="x0"
    )

parameters = [my_device, my_device2]

def auto_align() -> Generator[Msg, None, None]:

    det_pixels = centred_pixel(DEFAULT_DET, PIXEL_RANGE)
    dae = monitor_normalising_dae(
        det_pixels=det_pixels,
        frames=FRAMES,
        periods=PERIODS,
    )

    yield from bps.mv(dae.number_of_periods, COUNT)  # type: ignore

    yield from ensure_connected(my_device.get_movable(), dae)  # type: ignore

    yield from autoalign_utils.optimise_axis_against_intensity(
        dae=dae,
        alignment_param=my_device
        pre_align_plan=lambda: parameters[0].pre_align_params(parameters),
        
        # Before optimising my_device, moved my_device to 1.0 and my_device2 to 2.0 simultaneously.
    )

```

{py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.optimise_axis_against_intensity` also has parameters:

`fields` - The fields to use for the live table and human-readable file, what should be recorded.

`periods` - Whether to use periods.

`save_run` - Whether to save runs.

`num_points` - Number of points in a scan. More points means higher granularity and accuracy but costs time.

`files_output_dir` - Where to save any output files to on your system.

### AlignmentParam Continued

{py:obj}`ibex_bluesky_core.plans.reflectometry.autoalign_utils.AlignmentParam` has a parameter for `check_func`. This is a function that takes a `ModelResult` object and a float representing the value found when optimising the parameter, returning True or False meaning whether the value was found to **not** be sensible or if it is, respectively. An example of why you might want to do this is if you expect your value to be within a specific known range, and if its found to not be then you want the script to tell you. The following is how you can do this-

```python

def my_check_func(result: ModelResult, alignment_param_value: float) -> bool:

    expected_param_value = 1.0

    if not isclose(expected_param_value, alignment_param_value, abs_tol=expected_param_value_tol):
        return True # Not sensible

    return False # Sensible

my_device = AlignmentParam(
    name="my_device",
    rel_scan_ranges=[2.0],
    fit_method=Gaussian().fit(),
    fit_param="x0",
    check_func=my_check_func
    ) # my_check_func will be called after attempting to optimise the fitting parameter

```

If the optimised value is found to not be sensible then if you have provided a plan callback for the `problem_found_plan` parameter then this will be called here.
