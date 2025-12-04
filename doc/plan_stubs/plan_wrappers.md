# Plan wrappers

Plan wrappers that temporarily modify [DAE (Data Acquisition Electronics)](/devices/dae.md) settings during a plan, automatically restoring the original values afterwards. This ensures that your experiments don't permanently change instrument configuration.

## Available Wrappers

### {py:obj}`~dae_table_wrapper<ibex_bluesky_core.plan_stubs.with_dae_tables>`

A function that wraps a plan to temporarily modify the DAE wiring/detector/spectra tables.

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

(where `modified_settings` is a dataset in the form {py:obj}`~ibex_bluesky_core.devices.dae.DaeSettingsData`)



### {py:obj}`~ibex_bluesky_core.plan_stubs.with_num_periods`

A function that wraps a plan to temporarily modify the number of DAE software periods.

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


### {py:obj}`~ibex_bluesky_core.plan_stubs.with_time_channels`

A function that wraps a plan to temporarily modify the DAE time channel boundaries.

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
(where `modified_settings` is a dataset in the form {py:obj}`~ibex_bluesky_core.devices.dae.DaeTCBSettingsData`)

## Usage

To use these wrappers, pass a user plan as the first argument to the wrappers in this module:

``` python
from ibex_bluesky_core.plan_stubs import with_num_periods
from ibex_bluesky_core.devices.simpledae import SimpleDae

dae = SimpleDae() # Give your DAE options here

def plan():
    yield from with_num_periods(scan(...), dae=dae, number_of_periods=1000)
```

the plan with the modified DAE settings, restoring the original settings after the scan completes
(whether successfully or not).

