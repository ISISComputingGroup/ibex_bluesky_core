# Blocks

Blocks are one of IBEX's central abstractions, which present a uniform interface to any
scientifically interesting PV.

The {py:obj}`ibex_bluesky_core.devices.block` module provides support for four types of blocks:
- Read-only ({py:obj}`~ibex_bluesky_core.devices.block.BlockR`)
- Read/write ({py:obj}`~ibex_bluesky_core.devices.block.BlockRw`)
- Read/write with setpoint readback ({py:obj}`~ibex_bluesky_core.devices.block.BlockRwRbv`)
- Motors ({py:obj}`~ibex_bluesky_core.devices.block.BlockMot`)

```{note}
All signals in bluesky have a strong type. This must match
the underlying EPICS type of the PV, which helps to catch problems up-front rather than
 the middle of a plan. 
 
The following is an example error that will occur at the start of a plan, if trying to connect a `str` block to a `float` PV:
```{code}
ophyd_async.core._utils.NotConnected:
mot: NotConnected:
    setpoint_readback: TypeError: TE:NDW2922:CS:SB:mot:SP:RBV has type float not str
    setpoint: TypeError: TE:NDW2922:CS:SB:mot:SP has type float not str
    readback: TypeError: TE:NDW2922:CS:SB:mot has type float not str
```

## Block types

### Read-only ({py:obj}`~ibex_bluesky_core.devices.block.BlockR`)

This is a read-only block. It supports bluesky's {external+bluesky:py:obj}`~bluesky.protocols.Readable` protocol, as well as
basic metadata protocols such as {external+bluesky:py:obj}`~bluesky.protocols.HasName`.

This type of block is usable by:
- Plans like {external+bluesky:py:obj}`bluesky.plans.count` or {external+bluesky:py:obj}`bluesky.plans.scan` as a detector object.
- Plan stubs like {external+bluesky:py:obj}`bluesky.plan_stubs.rd`, which plans may use to get the current value
of a block for use within a plan.

A {py:obj}`~ibex_bluesky_core.devices.block.BlockR` object does not implement any logic on read - it simply returns the most recent
value of the block.

A simple constructor, {py:obj}`~ibex_bluesky_core.devices.block.block_r`, is available, which assumes the current instrument's PV
prefix:

```python
from ibex_bluesky_core.devices.block import block_r
readable_block = block_r(float, "my_block_name")
```

### Read-write ({py:obj}`~ibex_bluesky_core.devices.block.BlockRw`)

This is a read-write block. It supports the same protocols as a {py:obj}`~ibex_bluesky_core.devices.block.BlockR`, plus the {external+bluesky:py:obj}`~bluesky.protocols.Movable` protocol.

The addition of the {external+bluesky:py:obj}`~bluesky.protocols.Movable` protocol means that this type of block can be moved by plan 
stubs such as {external+bluesky:py:obj}`bluesky.plan_stubs.mv` or {external+bluesky:py:obj}`bluesky.plan_stubs.abs_set`.

It can also be used as the movable in full plans like {external+bluesky:py:obj}`bluesky.plans.scan`.

```{note}
 In bluesky terminology, any object with a `set()` method is 'Movable'. Therefore, a
 temperature controller is "moved" from one temperature to another, and a run title
 is also "moved" from one title to another.
 
 This is simply a matter of terminology - bluesky fully supports moving things which
 are not motors, even if the documentation tends to use motors as the examples.
```

A simple constructor, {py:obj}`~ibex_bluesky_core.devices.block.block_rw`, is available, which assumes the current instrument's PV
prefix:

```python
from ibex_bluesky_core.devices.block import block_rw, BlockWriteConfig
writable_block = block_rw(
    float, 
    "my_block_name",
    # Example: configure to always wait 5 seconds after being set.
    # For further options, see docstring of BlockWriteConfig.
    write_config=BlockWriteConfig(settle_time_s=5.0)
)
```


### Read/write/setpoint-readback ({py:obj}`~ibex_bluesky_core.devices.block.BlockRwRbv`)

This is a block with full support for reading and writing as per {py:obj}`~ibex_bluesky_core.devices.block.BlockRw`, but with
the addition of bluesky's {external+bluesky:py:obj}`~bluesky.protocols.Locatable` protocol, which allows you to read back the
current setpoint. Where possible, the setpoint will be read back from hardware.

This object is suitable for use in plan stubs such as `bluesky.plan_stubs.locate`.

This object is also more suitable for use in plans which use relative moves - the
relative move will be calculated with respect to the setpoint readback from hardware
(if available).

A simple constructor ({py:obj}`~ibex_bluesky_core.devices.block.block_rw_rbv`) is available:

```python
from ibex_bluesky_core.devices.block import block_rw_rbv, BlockWriteConfig
rw_rbv_block = block_rw_rbv(
    float, 
    "my_block_name",
    # Example: configure to always wait 5 seconds after being set.
    # For further options, see docstring of BlockWriteConfig.
    write_config=BlockWriteConfig(settle_time_s=5.0)
)
```

### Motors ({py:obj}`~ibex_bluesky_core.devices.block.BlockMot`)

This represents a block pointing at a motor record. This has support for:
- Reading ({external+bluesky:py:obj}`~bluesky.protocols.Readable`)
- Writing ({external+bluesky:py:obj}`~bluesky.protocols.Movable`)
- Limit-checking ({external+bluesky:py:obj}`~bluesky.protocols.Checkable`)
- Stopping (e.g. on scan abort) ({external+bluesky:py:obj}`~bluesky.protocols.Stoppable`)
- And advanced use-cases like fly-scanning

This type is recommended to be used if the underlying block is a motor record. It always has
type `float`, and as such does not take a type argument (unlike the other block types).

{external+bluesky:py:obj}`~bluesky.protocols.Checkable` means that moves which would eventually violate limits can be detected by
bluesky simulators, before the plan ever runs. This can help to catch errors before
the plan is executed against hardware. There is also limit-checking at runtime;
a {external+ophyd_async:py:obj}`~ophyd_async.epics.motor.MotorLimitsException` will be raised
at runtime if a requested position is outside the motor's limits.

{external+bluesky:py:obj}`~bluesky.protocols.Stoppable` means that the motor can be asked to stop by bluesky. Plans may choose to execute
a `stop()` on failure, or explicitly during a plan.

Similar to other block types, a utility constructor ({py:obj}`~ibex_bluesky_core.devices.block.block_mot`) is available; however, it does not
require an explicit type as motors are always of `float` data type:

```python
from ibex_bluesky_core.devices.block import block_mot
mot_block = block_mot("motor_block")
```

A motor block does not need an explicit write config: it always waits for the requested motion
to complete. See {py:obj}`~ibex_bluesky_core.devices.block.BlockMot` for a detailed mapping of
the usual write-configuration options and how these are instead achieved by a motor block.

## Configuring block write behaviour

{py:obj}`~ibex_bluesky_core.devices.block.BlockRw` and {py:obj}`~ibex_bluesky_core.devices.block.BlockRwRbv` both take a `write_config` argument, which can be used to configure
the behaviour on writing to a block, for example tolerances and settle times.

See {py:obj}`~ibex_bluesky_core.devices.block.BlockWriteConfig` for a detailed
description of the available options.

## Run Control

Run-control information is available via the {py:obj}`block.run_control <ibex_bluesky_core.devices.block.RunControl>` sub-device.
Both configuring and reading the current status of run control are permitted.

The signals available on the run-control subdevice are:
- `block.run_control.in_range`: Whether run-control is currently in-range (bool, read-only)
- `block.run_control.low_limit`: Low run-control limit (float, read-write)
- `block.run_control.high_limit`: High run-control limit (float, read-write)
- `block.run_control.suspend_if_invalid`: Whether to suspend data collection on invalid data (bool, read-write)
- `block.run_control.enabled`: Whether run-control is enabled (bool, read-write)
- `block.run_control.out_time`: Time, in seconds, for which run-control has been out-of-range (float, read-only)
- `block.run_control.in_time`: Time, in seconds, for which run-control has been in-range (float, read-only)

```{note}
Run control limits are always `float`, regardless of the datatype of the block.
```
