# 6. Where to put code

## Status

Current

## Context

We need to decide where to draw the line between this repository's responsibility and where to put technique-specific and instrument-specific plans and devices.

When we wrote initial plans on CRISP and LOQ we put everything in the instrument area and found we were duplicating a lot of stuff for common functionality ie. setting up DAEs, scanning one block, using the same callbacks etc.

We decided to put all the plans in this repo, but on HIFI and RIKENFE(+ARGUS and CHRONUS) we found that this was insufficiently flexible for tweaking lots of beamline devices and plans ie. magnet tolerances and so on.
There are different levels of use-cases where muons may need to be able to come in at a slightly lower level ie. adding lots of fits and doing back-to-back alignment scans, but these are generally specific to one instrument.

## Present

Tom & Jack H

## Decision

We should keep general and technique plans and devices in our repo, but let people write their own instrument-specific devices and plans too. These might use bits of ibex_bluesky_core, but have more flexibility. 

Examples of devices and where we would put them under this model:

### `ibex_bluesky_core` devices
- `BlockRw` and `SimpleDae`: `ibex_bluesky_core` as it's completely general / useful to all beamlines
- `ReflParameter`: in `ibex_bluesky_core.devices.reflectrometry` because it's useful across all reflectometers
- `Danfysik`: Try to push down "special" logic (i.e. polarity switching) into the IOC so that a standard `block_rw` works. Otherwise put in `ibex_bluesky_core.devices`

### `inst` scripts area devices
- `HifiMagnetAxis` (controls a shim coil of HIFI's cryomagnet): `inst.bluesky_devices` area on HIFI - it is only useful for one instrument

Examples of plans and where we would put them under this model:
### `ibex_bluesky_core` plans
- Scanning one block against DAE with a common set of callbacks
- Optimizing an axis against a readback (e.g. consituent parts of reflectometry auto-align)
- Very common plans
  - `scan_motor_against_dae`:
    * Always assumes a "motor" - i.e. sets up a block with `use_completion_callback=True` and `use_global_moving_flag=True`
  - `scan_refl_param_against_dae`:
    * A refl parameter can be constructed without any extra information
  - Both of the above are just thin wrappers around a lower-level plan.

### `inst` scripts area plans
- Full `auto_align` for POLREF for example with full axis-order and tolerances etc set for POLREF
  * Would be expected to *call* the optimizing axis against readback plan a bunch of times
- HIFI zero-field calibration/setup scan
- RIKEN auto-tuning - but like refl, might be able to use component plans that we keep in `ibex_bluesky_core`
- "top-level" plans that end users will actually call (though they may delegate almost immediately to `ibex_bluesky_core` helpers)

where `inst` plans/devices are kept in ie. `\instrument\settings\config\<>\configurations\python\inst\bluesky\{plans\devices}` respectively.

## Consequences
Negative: 
- anyone using their own, instrument-specific devices which do not use our helpers will need to be updated if we do things like change ophyd-async versions as this may break their devices and/or plans.
Positive
- less duplication between beamlines 
- if we update ie. the refl server, we only need to update one definition of the reflectometry parameter devices.
- if we find a bug in a common plan we can fix it
