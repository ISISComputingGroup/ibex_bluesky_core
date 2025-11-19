# General Plans 

The {py:obj}`ibex_bluesky_core.plans` module provides a number of plans that can be run by the RunEngine directly. These are mostly wrappers around the generic {external+bluesky:doc}`bluesky plans <plans>`.

All of these plans can be used directly by the RunEngine (`RE()`), or within a wrapper of your own that `yields from` these plans.

So you can do this: 

```python
from ibex_bluesky_core.plans.reflectometry import refl_scan
from ibex_bluesky_core.fitting import Gaussian


result = RE(refl_scan("S1VG", 1, 10, 21, model=Gaussian().fit(), frames=500, det=100, mon=3, pixel_range=6, periods=True, save_run=False))
```

or this: 

```python
from ibex_bluesky_core.plans.reflectometry import refl_scan
from ibex_bluesky_core.fitting import Gaussian


def my_plan():
    ...  # Some stuff before scan
    icc = yield from refl_scan("S1VG", 1, 10, 21, model=Gaussian().fit(), frames=500, det=100, mon=3, pixel_range=6, periods=True, save_run=False)
    ...  # Some stuff after scan
```

The scanning plans documented on this page will return a {py:obj}`~ibex_bluesky_core.callbacks.ISISCallbacks` instance, which can be used to access results of fits, centre of mass, and other callbacks:

```python
from ibex_bluesky_core.plans import motor_scan
def my_plan():
    icc = (yield from motor_scan("MyBlock1", 1, 10, 21, model=Gaussian().fit(), frames=500, det=100, mon=3, pixel_range=6, periods=True, save_run=False))
    print(icc.live_fit.result.fit_report())
    print(f"COM: {icc.com.result}")
```

## Plans taking _devices_ as arguments

These take "devices" so you can pass your own DAE object and a movable/readable but use a standard set of callbacks for plotting, fitting and log file writing. These are designed to allow flexibility such as more in-depth DAE customisation, block configuration ie write tolerances, settle times. 

- {py:obj}`ibex_bluesky_core.plans.scan` - this is an absolute/relative scan.
- {py:obj}`ibex_bluesky_core.plans.adaptive_scan` - this is for an adaptive/relative-adaptive scan.

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

which would be used on the console as: `RE(my_plan())`

## Plans taking _names_ as arguments

Alternatively, we provide some wrappers that construct the devices for you - these are:

- {py:obj}`ibex_bluesky_core.plans.motor_scan`
- {py:obj}`ibex_bluesky_core.plans.motor_adaptive_scan`

These plans take the _names_ of blocks as arguments, rather than devices, and construct a DAE and block device for you, using the global moving flag to determine if a motor has finished moving (in the same way as a `waitfor_move()`). This might be useful if you have a fairly standard DAE setup and want to scan a block pointing at a motor such as a Sample Changer axis, but is not as flexible or performant as the lower-level plans.

For example, to scan over a motor, wait for 400 frames, and perform a linear fit, you can write this in the console: 

```python
>>> from ibex_bluesky_core.plans import motor_scan
>>> from ibex_bluesky_core.fitting import Linear
>>> result = RE(motor_scan("motor_block", 1, 10, 11, model=Linear().fit(), frames=400, det=1, mon=3))
>>> result.plan_result.live_fit
```
