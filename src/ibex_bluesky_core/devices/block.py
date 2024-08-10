"""ophyd-async devices and utilities for communicating with IBEX blocks."""

import asyncio
from dataclasses import dataclass
from typing import Callable, Generic, Type, TypeVar

from bluesky.protocols import Locatable, Location, Movable
from ophyd_async.core import (
    AsyncStatus,
    HintedSignal,
    SignalR,
    SignalRW,
    StandardReadable,
    observe_value,
)
from ophyd_async.epics.signal import epics_signal_r, epics_signal_rw

"""Block data type"""
T = TypeVar("T")


__all__ = ["BlockR", "BlockRw", "BlockRwRbv", "BlockWriteConfiguration"]


@dataclass(kw_only=True)
class BlockWriteConfiguration(Generic[T]):
    """Configuration settings for writing to blocks.

    use_completion_callback: Whether to wait for an EPICS completion callback while setting
        this block. Defaults to true, which is appropriate for most blocks.

    set_success_func: An arbitrary function which is called to decide whether the block has
        set successfully yet or not. The function takes (setpoint, actual) as arguments and
        should return true if the value has successfully set and is "ready", or False otherwise.

        This can be used to implement arbitrary tolerance behaviour. For example:
        >>> def check(setpoint: T, actual: T) -> bool:
        >>>     return setpoint - 0.1 <= actual <= setpoint + 0.1

        If use_completion_callback is True, the completion callback must complete before
        set_success_func is ever called.

        Defaults to None, which means no check is applied.

    set_timeout_s: A timeout, in seconds, on the value being set successfully. The timeout
        applies to the EPICS completion callback (if enabled) and the set success function
        (if provided), and excludes any configured settle time.

        Defaults to None, which means no timeout.

    settle_time_s: A wait time, in seconds, which is unconditionally applied just before the set
        status is marked as complete. Defaults to zero.

    """

    use_completion_callback: bool = True
    set_success_func: Callable[[T, T], bool] | None = None
    set_timeout_s: float | None = None
    settle_time_s: float = 0.0


class _RunControl(StandardReadable):
    """Subdevice for common run-control signals."""

    def __init__(self, prefix: str, name: str = "") -> None:
        self.inrange = epics_signal_r(bool, f"{prefix}INRANGE")

        self.low_limit = epics_signal_rw(float, f"{prefix}LOW")
        self.high_limit = epics_signal_rw(float, f"{prefix}HIGH")

        self.suspend_if_invalid = epics_signal_rw(bool, f"{prefix}SOI")
        self.enabled = epics_signal_rw(bool, f"{prefix}ENABLE")

        self.out_time = epics_signal_r(float, f"{prefix}OUT:TIME")
        self.in_time = epics_signal_r(float, f"{prefix}IN:TIME")

        super().__init__(name=name)


class BlockR(StandardReadable, Generic[T]):
    """Device representing an IBEX readable block of arbitrary data type."""

    def __init__(self, datatype: Type[T], prefix: str, block_name: str) -> None:
        """Create a new read-only block."""
        with self.add_children_as_readables(HintedSignal):
            self.readback: SignalR[T] = epics_signal_r(datatype, f"{prefix}CS:SB:{block_name}")

        with self.add_children_as_readables():
            self.run_control = _RunControl(f"{prefix}CS:SB:{block_name}:RC:")

        super().__init__(name=block_name)
        self.readback.set_name(block_name)


class BlockRw(BlockR[T], Movable):
    """Device representing an IBEX read/write block of arbitrary data type."""

    def __init__(
        self,
        datatype: Type[T],
        prefix: str,
        block_name: str,
        *,
        write_config: BlockWriteConfiguration[T] | None = None,
    ) -> None:
        """Create a new read-write block.

        Args:
            datatype: the type of data in this block (e.g. str, int, float)
            prefix: the current instrument's PV prefix
            block_name: the name of the block
            write_config: Settings which control how this device will set the underlying PVs

        """
        with self.add_children_as_readables():
            self.setpoint: SignalRW[T] = epics_signal_rw(datatype, f"{prefix}CS:SB:{block_name}:SP")

        self._write_config = write_config or BlockWriteConfiguration()

        super().__init__(datatype=datatype, prefix=prefix, block_name=block_name)

    @AsyncStatus.wrap
    async def set(self, value: T) -> None:
        """Set the setpoint of this block."""

        async def do_set(setpoint: T) -> None:
            await self.setpoint.set(
                setpoint, wait=self._write_config.use_completion_callback, timeout=None
            )

            # Wait for the _set_success_func to return true.
            # This uses an "async for" to loop over items from observe_value, which is an async
            # generator. See documentation on "observe_value" or python "async for" for more details
            if self._write_config.set_success_func is not None:
                async for actual_value in observe_value(self.readback):
                    if self._write_config.set_success_func(setpoint, actual_value):
                        break

        async def set_and_settle(setpoint: T) -> None:
            if self._write_config.set_timeout_s is not None:
                await asyncio.wait_for(do_set(setpoint), timeout=self._write_config.set_timeout_s)
            else:
                await do_set(setpoint)

            await asyncio.sleep(self._write_config.settle_time_s)

        await set_and_settle(value)


class BlockRwRbv(BlockRw[T], Locatable):
    """Device representing an IBEX read/write/setpoint readback block of arbitrary data type."""

    def __init__(
        self,
        datatype: Type[T],
        prefix: str,
        block_name: str,
        *,
        write_config: BlockWriteConfiguration[T] | None = None,
    ) -> None:
        """Create a new read/write/setpoint readback block.

        Args:
            datatype: the type of data in this block (e.g. str, int, float)
            prefix: the current instrument's PV prefix
            block_name: the name of the block
            write_config: Settings which control how this device will set the underlying PVs

        """
        with self.add_children_as_readables():
            self.setpoint_readback: SignalR[T] = epics_signal_r(
                datatype, f"{prefix}CS:SB:{block_name}:SP:RBV"
            )

        super().__init__(
            datatype=datatype, prefix=prefix, block_name=block_name, write_config=write_config
        )

    async def locate(self) -> Location[T]:
        """Get the current 'location' of this block."""
        actual, sp_rbv = await asyncio.gather(
            self.readback.get_value(),
            self.setpoint_readback.get_value(),
        )
        return {
            "readback": actual,
            "setpoint": sp_rbv,
        }
