# SimpleDae controllers

The `Controller` class is responsible for starting and stopping acquisitions, in a generic
way.

# Predefined controllers

Some controllers have been predefined in the 
`ibex_bluesky_core.devices.simpledae.controllers` module.

## RunPerPointController

This controller starts and stops a new DAE run for each scan point. It can be configured to 
either end runs or abort them on completion.

This controller causes the following signals to be published by `SimpleDae`:

- `controller.run_number` - The run number into which data was collected. Only published 
  if runs are being saved.

## PeriodPerPointController

This controller begins a single DAE run at the start of a scan, and then counts into a new
DAE period for each individual scan point.

The DAE must be configured with enough periods in advance. This is possible to do from a
plan as follows:

```python
import bluesky.plan_stubs as bps
import bluesky.plans as bp
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.block import BlockRw


def plan():
    dae: SimpleDae = ...
    block: BlockRw = ...
    num_points = 20
    yield from bps.mv(dae.number_of_periods, num_points)
    yield from bp.scan([dae], block, 0, 10, num=num_points)
```

The controller causes the following signals to be published by `SimpleDae`:

- `simpledae.period_num` - the period number into which this scan point was counted.