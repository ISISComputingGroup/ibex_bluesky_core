# Plan Wrappers

Plan wrappers that temporarily modify DAE (Data Acquisition Electronics) settings during a plan, automatically restoring the original values afterwards. This ensures that your experiments don't permanently change instrument configuration.

## Available Wrappers

['dae_table_wrapper](ibex_bluesky_core.plan_stubs.dae_table_wrapper)
['num_periods_wrapper](ibex_bluesky_core.plan_stubs.num_periods_wrapper)
['time_channels_wrapper](ibex_bluesky_core.plan_stubs.time_channels_wrapper)

## Usage

To use these wrappers, the plan written by the user must be wrapped by the function within the RunEngine:

``` python

from bluesky import RunEngine
from ibex_bluesky_core.plan_stubs import with_num_periods
from ibex_bluesky_core.devices.simpledae import SimpleDae

dae = SimpleDae() # Give your DAE options here
RE = RunEngine()

modified_settings = 1

def example_plan():
    yield from bps.mv(dae.number_of_periods, modified_settings)

RE(
    with_num_periods(
        example_plan(), 
        dae=dae,
        )
    )

```

the plan with the modified DAE settings, restoring the original settings afterwards.

