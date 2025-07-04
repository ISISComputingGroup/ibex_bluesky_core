# Redefinition

The plan stubs in this module implement 'redefinition' of a parameter, where supported. That is, no physical movement
occurs, but the reported position changes to the given position.

## `redefine_motor`

The {py:obj}`ibex_bluesky_core.plan_stubs.redefine_motor` plan stub can be used to redefine the current
position of a motor (for example a {py:obj}`ibex_bluesky_core.devices.block.BlockMot`) to a new value.

The motor does not physically move, but after this plan stub executes, the current position will be defined
as `value`.

```python
from ibex_bluesky_core.plan_stubs import redefine_motor
from ibex_bluesky_core.devices.block import block_mot, BlockMot
import bluesky.plan_stubs as bps


def my_plan():
    motor: BlockMot = block_mot("my_motor")
    optimimum_value: float = ...
    
    # Physically move the motor to it's optimum position
    yield from bps.mv(motor, optimimum_value)
    
    # Redefine the current position as zero
    yield from redefine_motor(motor, 0.)
```

By default, the {py:obj}`redefine_motor <ibex_bluesky_core.plan_stubs.redefine_motor>`
plan stub sleeps for 1 second after redefining the motor. This avoids race conditions, where a motor is moved too soon
after being redefined to a new position, and the redefined position has not yet been read back from the controller.
This behaviour can be controlled with the `sleep` keyword argument to
{py:obj}`redefine_motor <ibex_bluesky_core.plan_stubs.redefine_motor>`.

## `redefine_refl_parameter`

The {py:obj}`ibex_bluesky_core.plan_stubs.redefine_refl_parameter` plan stub can be used to redefine the current
position of a {py:obj}`ibex_bluesky_core.devices.reflectometry.ReflParameter` to a new value. Note that some reflectometry parameters ie. `Theta` cannot be redefined, so these must be constructed with `has_redefine=False`. This plan stub will handle this case and raise an error if a user tries to redefine it. 

This plan stub has an identical API to that of the {py:obj}`ibex_bluesky_core.plan_stubs.redefine_motor` plan stub
described above, but operates on a reflectometry parameter rather than a motor.
