# Plan Wrappers

Plan wrappers that temporarily modify [DAE (Data Acquisition Electronics)](https://isiscomputinggroup.github.io/ibex_bluesky_core/devices/dae.html#dae-data-acquisition-electronics) settings during a plan, automatically restoring the original values afterwards. This ensures that your experiments don't permanently change instrument configuration.

## Available Wrappers

### DAE Table

:py:obj:`dae_table_wrapper <ibex_bluesky_core.plan_stubs.dae_table_wrapper>`

```python
RE(
    _with_dae_tables(
        bps.null(),
        dae=dae,
        new_settings=modified_settings
        )
    )
```

Where `modified_settings` is a dataset in the form :py:obj:`DaeSettingsData < ibex_bluesky_core.devices.dae.DaeSettingsData>`

A function that wraps a plan to temporarily modify the DAE table.

### Num Periods
:py:obj:`num_periods_wrapper <ibex_bluesky_core.plan_stubs.num_periods_wrapper>`

```python
RE(
    _with_num_periods(
        bps.null(),
        dae=dae,
        number_of_periods=1000 
        )
    )
```
A function that wraps a plan to temporarily modify the number of periods.

### Time Channels
:py:obj:`time_channels_wrapper <ibex_bluesky_core.plan_stubs.time_channels_wrapper>`:

```python
RE(
    _with_time_channels(
        bps.null(),
        dae=dae,
        new_settings=modified_settings
        )
    )
```
Where `modified_settings` is a dataset in the form :py:obj:`DaeTCBSettingsData < ibex_bluesky_core.devices.dae.DaeTCBSettingsData>`

A function that wraps a plan to temporarily modify the time channels boundaries.

## Usage

To use these wrappers, the plan written by the user must be wrapped by the function within the RunEngine:

``` python

from bluesky import RunEngine
from ibex_bluesky_core.plan_stubs import _with_num_periods
from ibex_bluesky_core.devices.simpledae import SimpleDae

dae = SimpleDae() # Give your DAE options here
RE = RunEngine()

RE(
    _with_num_periods(
        bps.null(), # Default plan to run
        dae=dae,
        number_of_periods=1000 # Temporary number of periods to run
        )
    )

```

the plan with the modified DAE settings, restoring the original settings afterwards.

