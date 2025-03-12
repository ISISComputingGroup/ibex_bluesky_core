# Plans 

`ibex_bluesky_core` provides a number of plans that can be run by the RunEngine directly. 

These take "devices" so you can pass your own DAE object and a movable/readable: 

[`scan`](ibex_bluesky_core.plans.scan) - this is for a absolute/relative scan.

[`adaptive_scan`](ibex_bluesky_core.plans.adaptive_scan) - this is for an adaptive/relative-adaptive scan.

[`polling_plan`](ibex_bluesky_core.plans.polling_plan) - this is used for moving a motor and dropping updates from a "readable" if no motor updates are provided. An example of this is a laser reading which updates much more quickly than a motor might register it's moved, so the laser readings are not really useful information. 

Alternatively, we provide some very thin wrappers which construct the devices for you - these are:

[`motor_scan`](ibex_bluesky_core.plans.motor_scan)

[`motor_adaptive_scan`](ibex_bluesky_core.plans.motor_scan)

which wrap the above. These take _names_ of blocks, rather than devices themselves, and construct a DAE and block device for you. This might be useful if you have a fairly standard DAE setup and just want to scan a block pointing at a motor such as a Sample Changer axis.

The scanning plans will return an [`ISISCallbacks`](ibex_bluesky_core.callbacks.ISISCallbacks) instance, which gives results of fits, centre of masses etc. - for example in your own plan:

```python
from ibex_bluesky_core.plans import motor_scan
def my_plan():
    icc = (yield from motor_scan(...))
    print(icc.live_fit.result.fit_report())
    print(f"COM: {icc.peak_stats['com']}")
```


## Technique-specific plans

### Reflectometry

[`refl_scan`](ibex_bluesky_core.plans.reflectometry.refl_scan)

[`refl_adaptive_scan`](ibex_bluesky_core.plans.reflectometry.refl_adaptive_scan)

These are very similar to the above plans but are designed to construct a DAE and a [`ReflParameter`](ibex_bluesky_core.devices.reflectometry.ReflParameter) given a reflectometry server parameter name. These have some logic in the reflectometry server which tell us if sets were successful and so on. 

