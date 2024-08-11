# Blocks

Blocks are one of IBEX's central abstractions, which present a uniform interface to any
scientifically interesting PV.

`ibex_bluesky_core` has support for four types of blocks:
- Read-only
- Read/write
- Read/write with setpoint readback
- Motors

> **_ℹ️_**  
> All signals, including blocks, in bluesky have a strong type. This must match
> the underlying EPICS type of the PV, which helps to catch problems up-front rather than
>  the middle of a plan. Example error at the start of a plan, from trying to connect a `str` block to a `float` PV:
> ```
> ophyd_async.core._utils.NotConnected:
> mot: NotConnected:
>     setpoint_readback: TypeError: TE:NDW2922:CS:SB:mot:SP:RBV has type float not str
>     setpoint: TypeError: TE:NDW2922:CS:SB:mot:SP has type float not str
>     readback: TypeError: TE:NDW2922:CS:SB:mot has type float not str
> ```

## Block types

### `block_r` (read-only)

This is a read-only block. It supports `bluesky`'s `Readable` protocol, as well as
basic metadata protocols such as `HasName`.

This type of block is usable by:
- Plans like `bluesky.plans.count()` or `bluesky.plans.scan()` as a detector object.
- Plan stubs like `bluesky.plan_stubs.rd()`, which plans may use to get the current value
of a block easily for use in the plan.

A `BlockR` object does not implement any logic on read - it simply returns the most recent
value of the block.

A simple constructor, `block_r`, is available, which assumes the current instrument's PV
prefix.

### `block_rw` (read, write)

This is a read-write block. It supports all of the same protocols as `BlockR`, with the
addition of the `Movable` protocol.

The addition of the movable protocol means that this type of block can be moved by plan 
stubs such as `bluesky.plan_stubs.mv()` or `bluesky.plan_stubs.abs_set()`.

It can also be used as a `Movable` in full plans like `bluesky.plans.scan()`.

> **_ℹ️_**  
> In bluesky terminology, any object with a `set()` method is `Movable`. Therefore, a
> temperature controller is "moved" from one temperature to another, and a run title
> may equally be "moved" from one value to the next.
> 
> This is simply a matter of terminology - bluesky fully supports moving things which
> are not motors, even if the documentation tends to use motors as the examples.

### `block_rw_rbv` (read, write, setpoint readback)

This is a block with full support for reading and writing as per `BlockRw`, but with
the addition of `bluesky`'s `Locatable` protocol, which allows you to read back the
current setpoint. Where possible, the setpoint will be read back from hardware.

This object is suitable for use in plan stubs such as `bluesky.plan_stubs.locate()`.

### `block_mot` (motor-specific)

This represents a block pointing at a motor record. This has support for:
- Reading (`Readable`)
- Writing (`Movable`)
- Limit-checking (`Checkable`)
- Stopping (e.g. on scan abort) (`Stoppable`)
- And advanced use-cases like fly-scanning

This type is recommended to be used if the underlying block is a motor record. It always has
type `float`, and as such does not take a type argument (unlike the other block types).

## Configuring block write behaviour

`BlockRw` and `BlockRwRbv` both take a `write_config` argument, which can be used to configure
the behaviour on writing to a block, for example tolerances and settle times.

See the docstring on `ibex_bluesky_core.devices.block.BlockWriteConfig` for a detailed
description of all the options which are available.

## Run control

Run control information is available via the `block.run_control` sub-device.

Both configuring and reading the current status of run control are permitted.

> **_ℹ️_**  
> Run control limits are always `float`, regardless of the datatype of the block.
