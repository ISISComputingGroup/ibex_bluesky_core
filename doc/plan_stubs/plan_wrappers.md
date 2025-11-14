# Plan wrappers

Plan wrappers that temporarily modify [DAE (Data Acquisition Electronics)](/devices/dae.md) settings during a plan, automatically restoring the original values afterwards. This ensures that your experiments don't permanently change instrument configuration.

## Available Wrappers

### DAE Table

A function that wraps a plan to temporarily modify the DAE table.

API reference: {py:obj}`dae_table_wrapper<ibex_bluesky_core.plan_stubs.with_dae_tables>`

```python
RE(
    with_dae_tables(
        bps.null(),
        dae=dae,
        new_settings=modified_settings
    )
)
```
```python
def plan():
    yield from with_dae_tables(scan(...), dae=dae, new_settings=modified_settings)
```

(where `modified_settings` is a dataset in the form {py:obj}`DaeSettingsData <ibex_bluesky_core.devices.dae.DaeSettingsData>`)



### Num Periods

A function that wraps a plan to temporarily modify the number of periods.

API reference: {py:obj}`num_periods_wrapper<ibex_bluesky_core.plan_stubs.with_num_periods>`

```python
RE(
    with_num_periods(
        bps.null(),
        dae=dae,
        number_of_periods=1000 
    )
)
```
```python
def plan():
    yield from with_num_periods(scan(...), dae=dae, number_of_periods=1000)
```


### Time Channels
A function that wraps a plan to temporarily modify the time channels boundaries.

API reference: {py:obj}`time_channels_wrapper<ibex_bluesky_core.plan_stubs.with_time_channels>`

```python
RE(
    with_time_channels(
        bps.null(),
        dae=dae,
        new_settings=modified_settings
    )
)
```
```python
def plan():
    yield from with_time_channels(scan(...), dae=dae, new_settings=modified_settings)
```
(where `modified_settings` is a dataset in the form {py:obj}`DaeTCBSettingsData<ibex_bluesky_core.devices.dae.DaeTCBSettingsData>`)

## Usage

To use these wrappers, the plan written by the user must be wrapped by the function within the RunEngine:

``` python
from ibex_bluesky_core.plan_stubs import with_num_periods
from ibex_bluesky_core.devices.simpledae import SimpleDae

dae = SimpleDae() # Give your DAE options here

def plan():
    yield from with_num_periods(scan(...), dae=dae, number_of_periods=1000)
```

the plan with the modified DAE settings, restoring the original settings afterwards.

