# General Plans 

`ibex_bluesky_core` provides a number of plans that can be run by the RunEngine directly. These are mostly thin wrappers around the generic [bluesky plans](https://blueskyproject.io/bluesky/main/plans.html)

All of these plans can be used directly by the RunEngine (`RE()`) or within a wrapper of your own that yields from them (`yield from`)

So you can do this: 

```python
result = RE(refl_scan("S1VG", 1, 10, 21, model=Gaussian().fit() frames=500, det=100, mon=3, pixel_range=6, periods=True, save_run=False))
```

or this: 

```python
from ibex_bluesky_core.plans.reflectometry import refl_scan
def my_plan():
    ...  # Some stuff before scan
    icc = (yield from refl_scan("S1VG", 1, 10, 21, model=Gaussian().fit() frames=500, det=100, mon=3, pixel_range=6, periods=True, save_run=False))
    ...  # Some stuff after scan
```

## Return values

The scanning plans documented on this page will return an [`ISISCallbacks`](ibex_bluesky_core.callbacks.ISISCallbacks) instance, which gives results of fits, centre of masses etc. - for example in your own plan if you wanted to print the fit result and the centre of mass:

```python
from ibex_bluesky_core.plans import motor_scan
def my_plan():
    icc = (yield from motor_scan("MyBlock1", 1, 10, 21, model=Gaussian().fit() frames=500, det=100, mon=3, pixel_range=6, periods=True, save_run=False))
    print(icc.live_fit.result.fit_report())
    print(f"COM: {icc.peak_stats['com']}")
```

## Lower-level plans

These take "devices" so you can pass your own DAE object and a movable/readable but use a standard set of callbacks for plotting, fitting and log file writing. These are designed to allow flexibility such as more in-depth DAE customisation, block configuration ie write tolerances, settle times. 

[`scan`](ibex_bluesky_core.plans.scan) - this is for a absolute/relative scan.

[`adaptive_scan`](ibex_bluesky_core.plans.adaptive_scan) - this is for an adaptive/relative-adaptive scan.

[`polling_plan`](ibex_bluesky_core.plans.polling_plan) - this is used for moving a motor and dropping updates from a "readable" if no motor updates are provided. An example of this is a laser reading which updates much more quickly than a motor might register it's moved, so the laser readings are not really useful information.

An example of using one of these could be: 

```python
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.block import BlockRw, BlockWriteConfig
from ibex_bluesky_core.plans import scan
from ibex_bluesky_core.fitting import Linear

def my_plan():
    dae = SimpleDae(...) # Give your DAE options here
    block = BlockRw("my_block", write_config=BlockWriteConfig(settle_time_s=5)) # This block needs a settle time of 5 seconds
    icc = (yield from scan(dae, block, 1, 10, 21, model=Linear().fit()))
    print(icc.peak_stats['com']) # print the centre of mass

```

which would be used on the console like so: `RE(my_plan)`

## Higher-level wrapper plans 
Alternatively, we provide some very thin wrappers which construct the devices for you - these are:

[`motor_scan`](ibex_bluesky_core.plans.motor_scan)

[`motor_adaptive_scan`](ibex_bluesky_core.plans.motor_scan)

which wrap the above respectively. These take _names_ of blocks, rather than devices themselves, and construct a DAE and block device for you. This might be useful if you have a fairly standard DAE setup and just want to scan a block pointing at a motor such as a Sample Changer axis.

for example if you just wanted to scan over a motor, wait for 400 frames, and perform a linear fit, you can just write this in the console: 

```python
>>> from ibex_bluesky_core.plans import motor_scan
>>> from ibex_bluesky_core.fitting import Linear
>>> result = RE(motor_scan("motor_block", 1, 10, 11, model=Linear().fit(), frames=400, det=1, mon=3))
>>> result.plan_result.live_fit
```
