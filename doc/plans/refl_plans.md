# Reflectometry Plans

For reflectometers- we provide a few generic plans which can be used to align beamlines.

## AlignmentParam

An AlignmentParam represents a device on your beamline that needs to be optimised against the intensity of the beam. It is a wrapper around ReflParameter, of which is used to be able to move the device. To instantiate an AlignmentParam you should do the following as a minimum-

```python
... # Other imports
from ibex_bluesky_core.plans.reflectometry.autoalign_utils import AlignmentParam

my_device = AlignmentParam(
    name="my_device",
    rel_scan_ranges=[2.0],
    fit_method=Gaussian().fit()
    )
```

`name` - Should be the same as the corresponding reflectometry parameter.

`rel_scan_ranges` - This is used for when it comes to scanning over the device. A range represents the distance the device will move, with the current device position at the centre of this. E.g passing `[2.0]` means that the device will be scanned between `device_pos - 1.0` and `device_pos + 1.0`, for a total range of `2.0`. Note that this is a list, so providing more than one scan range will mean that subsequent scans will happen. If you provide multiple scan ranges of decreasing value then this could result in the plan finding a result closer to an optimum.

`fit_method` - When scanning over the device against beam intensity, what shape of data you would expect to find.

### Pre-align Parameters

To build on the above, the constructor for AlignmentParam also has an option for assigning positions to other AlignmentParams, used in the following manner-

```python
... # Other imports
from ibex_bluesky_core.plans.reflectometry.autoalign_utils import AlignmentParam

my_device = AlignmentParam(
    name="my_device",
    rel_scan_ranges=[2.0],
    fit_method=Gaussian().fit(),
    pre_align_param_positions={"my_device": 1.0, "my_device2": 2.0}
    )
```

`pre_align_param_positions` is a dictionary of `AlignmentParam` name to a motor position. So in the above example we expect `"my_device"` to move to `1.0` and `"my_device2"` to move to `2.0`. To perform these moves the `pre_align_params` method can be called.

```python
... # Code from above

my_device2 = AlignmentParam(
    name="my_device2",
    rel_scan_ranges=[1.0],
    fit_method=Gaussian().fit()
    )

parameters = [my_device, my_device2]

yield from my_device.pre_align_params(parameters)
# This will move my_device to 1.0 and my_device2 to 2.0 simultaneously

```

Note that there is also a `get_movable` method which returns a `AlignmentParam`'s underlying `ReflParameter `object.

## Full-Auto Alignment Plan

The idea for how we expect the main auto-alignment plan to be used is that at the top / instrument level, a list of `AlignmentParam`s, are to be optimised against the intensity of the beam; whereby the plan is ran once for each element, in the order of the provided list. After each `AlignmentParam` is optimised, their `pre_align_params` method is called using the list of all `AlignmentParam`s so that they are all moved to some preset position. The following is how you make a simple call to this plan (`optimise_axis_against_intensity`)-

```python

my_device = AlignmentParam(
    name="my_device",
    rel_scan_ranges=[2.0],
    fit_method=Gaussian().fit(),
    pre_align_param_positions={"my_device": 1.0, "my_device2": 2.0}
    )

parameters = [my_device, my_device2]

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
