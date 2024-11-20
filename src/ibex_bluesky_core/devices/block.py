"""ophyd-async devices and utilities for communicating with IBEX blocks."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Generic, Type, TypeVar

from bluesky.protocols import Locatable, Location, Movable, Triggerable
from ophyd_async.core import (
    AsyncStatus,
    HintedSignal,
    SignalR,
    SignalRW,
    StandardReadable,
    observe_value,
)
from ophyd_async.epics.motor import Motor
from ophyd_async.epics.signal import epics_signal_r, epics_signal_rw

from ibex_bluesky_core.devices import get_pv_prefix

logger = logging.getLogger(__name__)

# Block data type
T = TypeVar("T")


__all__ = [
    "BlockMot",
    "BlockR",
    "BlockRw",
    "BlockRwRbv",
    "BlockWriteConfig",
    "RunControl",
    "block_mot",
    "block_r",
    "block_rw",
    "block_rw_rbv",
]


@dataclass(kw_only=True)
class BlockWriteConfig(Generic[T]):
    """Configuration settings for writing to blocks.

    use_completion_callback:
        Whether to wait for an EPICS completion callback while setting
        this block. Defaults to true, which is appropriate for most blocks.

    set_success_func:
        An arbitrary function which is called to decide whether the block has
        set successfully yet or not. The function takes (setpoint, actual) as arguments and
        should return true if the value has successfully set and is "ready", or False otherwise.

        This can be used to implement arbitrary tolerance behaviour. For example::

            def check(setpoint: T, actual: T) -> bool:
                return setpoint - 0.1 <= actual <= setpoint + 0.1

        If use_completion_callback is True, the completion callback must complete before
        set_success_func is ever called.

        Executing this function should be "fast" (i.e. the function should not sleep), and it should
        not do any external I/O.

        Defaults to None, which means no check is applied.

    set_timeout_s:
        A timeout, in seconds, on the value being set successfully. The timeout
        applies to the EPICS completion callback (if enabled) and the set success function
        (if provided), and excludes any configured settle time.

        Defaults to None, which means no timeout.

    settle_time_s:
        A wait time, in seconds, which is unconditionally applied just before the set
        status is marked as complete. Defaults to zero.

    """

    use_completion_callback: bool = True
    set_success_func: Callable[[T, T], bool] | None = None
    set_timeout_s: float | None = None
    settle_time_s: float = 0.0


class RunControl(StandardReadable):
    """Subdevice for common run-control signals."""

    def __init__(self, prefix: str, name: str = "") -> None:
        """Create a run control wrapper for a block.

        Usually run control should be accessed via the run_control property on a block, rather
        than by constructing an instance of this class directly.

        Args:
            prefix: the run-control prefix, e.g. "IN:INSTRUMENT:CS:SB:blockname:RC:"
            name: ophyd device name

        """
        with self.add_children_as_readables(HintedSignal):
            # When explicitly reading run control, the most obvious signal that people will be
            # interested in is whether the block is in range or not.
            self.in_range = epics_signal_r(bool, f"{prefix}INRANGE")

        self.low_limit = epics_signal_rw(float, f"{prefix}LOW")
        self.high_limit = epics_signal_rw(float, f"{prefix}HIGH")

        self.suspend_if_invalid = epics_signal_rw(bool, f"{prefix}SOI")
        self.enabled = epics_signal_rw(bool, f"{prefix}ENABLE")

        self.out_time = epics_signal_r(float, f"{prefix}OUT:TIME")
        self.in_time = epics_signal_r(float, f"{prefix}IN:TIME")

        super().__init__(name=name)


class BlockR(StandardReadable, Triggerable, Generic[T]):
    """Device representing an IBEX readable block of arbitrary data type."""

    def __init__(self, datatype: Type[T], prefix: str, block_name: str) -> None:
        """Create a new read-only block.

        Args:
            datatype: the type of data in this block (e.g. str, int, float)
            prefix: the current instrument's PV prefix
            block_name: the name of the block

        """
        with self.add_children_as_readables(HintedSignal):
            self.readback: SignalR[T] = epics_signal_r(datatype, f"{prefix}CS:SB:{block_name}")

        # Run control doesn't need to be read by default
        self.run_control = RunControl(f"{prefix}CS:SB:{block_name}:RC:")

        super().__init__(name=block_name)
        self.readback.set_name(block_name)

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        """Blocks need to be triggerable to be used in adaptive scans.

        They do not do anything when triggered.
        """

    def __repr__(self) -> str:
        """Debug representation of this block."""
        return f"{self.__class__.__name__}(name={self.name})"


class BlockRw(BlockR[T], Movable):
    """Device representing an IBEX read/write block of arbitrary data type."""

    def __init__(
        self,
        datatype: Type[T],
        prefix: str,
        block_name: str,
        *,
        write_config: BlockWriteConfig[T] | None = None,
    ) -> None:
        """Create a new read-write block.

        The setpoint is not added to read() by default. For most cases where setpoint readback
        functionality is desired, BlockRwRbv is a more suitable type.

        If you *explicitly* need to read the setpoint from a BlockRw, you can do so in a plan with::

            import bluesky.plan_stubs as bps
            block: BlockRw = ...
            bps.read(block.setpoint)

        But note that this does not read back the setpoint from hardware, but rather the setpoint
        which was last sent by EPICS.

        Args:
            datatype: the type of data in this block (e.g. str, int, float)
            prefix: the current instrument's PV prefix
            block_name: the name of the block
            write_config: Settings which control how this device will set the underlying PVs

        """
        self.setpoint: SignalRW[T] = epics_signal_rw(datatype, f"{prefix}CS:SB:{block_name}:SP")

        self._write_config: BlockWriteConfig[T] = write_config or BlockWriteConfig()

        super().__init__(datatype=datatype, prefix=prefix, block_name=block_name)

    @AsyncStatus.wrap
    async def set(self, value: T) -> None:
        """Set the setpoint of this block."""

        async def do_set(setpoint: T) -> None:
            logger.info("Setting Block %s to %s", self.name, setpoint)
            await self.setpoint.set(
                setpoint, wait=self._write_config.use_completion_callback, timeout=None
            )
            logger.info("Got completion callback from setting block %s to %s", self.name, setpoint)

            # Wait for the _set_success_func to return true.
            # This uses an "async for" to loop over items from observe_value, which is an async
            # generator. See documentation on "observe_value" or python "async for" for more details
            if self._write_config.set_success_func is not None:
                logger.info(
                    "Waiting for set_success_func on setting block %s to %s", self.name, setpoint
                )
                async for actual_value in observe_value(self.readback):
                    if self._write_config.set_success_func(setpoint, actual_value):
                        break

        async def set_and_settle(setpoint: T) -> None:
            if self._write_config.set_timeout_s is not None:
                await asyncio.wait_for(do_set(setpoint), timeout=self._write_config.set_timeout_s)
            else:
                await do_set(setpoint)

            logger.info(
                "Waiting for configured settle time (%f seconds) on block %s",
                self._write_config.settle_time_s,
                self.name,
            )
            await asyncio.sleep(self._write_config.settle_time_s)

        await set_and_settle(value)
        logger.info("block set complete %s value=%s", self.name, value)


class BlockRwRbv(BlockRw[T], Locatable):
    """Device representing an IBEX read/write/setpoint readback block of arbitrary data type."""

    def __init__(
        self,
        datatype: Type[T],
        prefix: str,
        block_name: str,
        *,
        write_config: BlockWriteConfig[T] | None = None,
    ) -> None:
        """Create a new read/write/setpoint readback block.

        The setpoint readback is added to read(), but not hints(), by default. If you do not need
        a setpoint readback, choose BlockRw instead of BlockRwRbv.

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
        logger.info("locating block %s", self.name)
        actual, sp_rbv = await asyncio.gather(
            self.readback.get_value(),
            self.setpoint_readback.get_value(),
        )
        return {
            "readback": actual,
            "setpoint": sp_rbv,
        }


class BlockMot(Motor):
    """Device representing an IBEX block pointing at a motor."""

    def __init__(
        self,
        prefix: str,
        block_name: str,
    ) -> None:
        """Create a new motor-record block.

        The 'BlockMot' object supports motion-specific functionality such as:
        - Stopping if a scan is aborted (supports the bluesky 'Stoppable' protocol)
        - Limit checking (before a move starts - supports the bluesky 'Checkable' protocol)
        - Automatic calculation of move timeouts based on motor velocity
        - Fly scanning

        However, it generally relies on the underlying motor being "well-behaved". For example, a
        motor which does many retries may exceed the simple default timeout based on velocity (it
        is possible to explicitly specify a timeout on set() to override this).

        Blocks pointing at motors do not take a BlockWriteConfiguration parameter, as these
        parameters duplicate functionality which already exists in the motor record. The mapping is:

        use_completion_callback:
            Motors always use completion callbacks to check whether motion has completed. Whether to
            wait on that completion callback can be configured by the 'wait' keyword argument on
            set().
        set_success_func:
            Use .RDBD and .RTRY to control motor retries if the position has not been reached to
            within a specified tolerance. Note that motors which retry a lot may exceed the default
            motion timeout which is calculated based on velocity, distance and acceleration.
        set_timeout_s:
            A suitable timeout is calculated automatically based on velocity, distance and
            acceleration as defined on the motor record. This may be overridden by the 'timeout'
            keyword-argument on set().
        settle_time_s:
            Use .DLY on the motor record to configure this.
        """
        self.run_control = RunControl(f"{prefix}CS:SB:{block_name}:RC:")

        # GWBLOCK aliases .VAL to .RBV on a motor record for a block pointing at MOT:MTRxxxx.RBV,
        # which is what we have recommended to our users for motor blocks... That means that you
        # can't write to .VAL on a motor block. ophyd_async (reasonably) assumes you can write to
        # .VAL for a motor which you want to move.
        #
        # However, we also have motor record aliases for :SP and :SP:RBV, which *don't* get mangled
        # by GWBLOCK in that way. So by pointing at CS:SB:blockname:SP:RBV rather than
        # CS:SB:blockname here, we avoid a write access exception when moving a motor block.
        super().__init__(f"{prefix}CS:SB:{block_name}:SP:RBV", name=block_name)

    def __repr__(self) -> str:
        """Debug representation of this block."""
        return f"{self.__class__.__name__}(name={self.name})"


def block_r(datatype: Type[T], block_name: str) -> BlockR[T]:
    """Get a local read-only block for the current instrument.

    See documentation of BlockR for more information.
    """
    return BlockR(datatype=datatype, prefix=get_pv_prefix(), block_name=block_name)


def block_rw(
    datatype: Type[T], block_name: str, *, write_config: BlockWriteConfig[T] | None = None
) -> BlockRw[T]:
    """Get a local read-write block for the current instrument.

    See documentation of BlockRw for more information.
    """
    return BlockRw(
        datatype=datatype, prefix=get_pv_prefix(), block_name=block_name, write_config=write_config
    )


def block_rw_rbv(
    datatype: Type[T], block_name: str, *, write_config: BlockWriteConfig[T] | None = None
) -> BlockRwRbv[T]:
    """Get a local read/write/setpoint readback block for the current instrument.

    See documentation of BlockRwRbv for more information.
    """
    return BlockRwRbv(
        datatype=datatype, prefix=get_pv_prefix(), block_name=block_name, write_config=write_config
    )


def block_mot(block_name: str) -> BlockMot:
    """Get a local block pointing at a motor record for the local instrument.

    See documentation of BlockMot for more information.
    """
    return BlockMot(prefix=get_pv_prefix(), block_name=block_name)
