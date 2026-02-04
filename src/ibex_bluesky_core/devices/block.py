"""bluesky devices and utilities for communicating with IBEX blocks."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from bluesky.protocols import (
    HasName,
    Locatable,
    Location,
    Movable,
    NamedMovable,
    Triggerable,
)
from ophyd_async.core import (
    CALCULATE_TIMEOUT,
    AsyncStatus,
    CalculatableTimeout,
    SignalDatatype,
    SignalR,
    SignalRW,
    StandardReadable,
    StandardReadableFormat,
    WatchableAsyncStatus,
    observe_value,
    wait_for_value,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw
from ophyd_async.epics.motor import Motor

from ibex_bluesky_core.utils import get_pv_prefix

logger = logging.getLogger(__name__)

# Block data type
T = TypeVar("T", bound=SignalDatatype)


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
    "block_w",
]

# When using the global moving flag, we want to give IOCs enough time to update the
# global flag before checking it. This is an amount of time always applied before
# looking at the global moving flag.
GLOBAL_MOVING_FLAG_PRE_WAIT = 0.1


@dataclass(kw_only=True, frozen=True)
class BlockWriteConfig(Generic[T]):
    """Configuration settings for writing to blocks.

    These settings control how a block write is determined to be 'complete'. A block
    write should only be marked as complete when the equipment has physically reached
    the correct state, not just when the equipment has been told to move to the correct
    state.

    For example, during a scan of a block against a detector, the detector will be read
    as soon as the block declares the write as 'complete'.
    """

    use_completion_callback: bool = True
    """
    Whether to wait for an EPICS completion callback while setting
    this block. Defaults to :py:obj:`True`, which is appropriate for most blocks.
    """

    set_success_func: Callable[[T, T], bool] | None = None
    """
    An arbitrary function which is called to decide whether the block has
    set successfully yet or not. The function takes ``(setpoint, actual)`` as arguments and
    should return :py:obj:`True` if the value has successfully set and is "ready", or
    :py:obj:`False` otherwise.

    This can be used to implement arbitrary tolerance behaviour. For example::

        def check(setpoint: T, actual: T) -> bool:
            return setpoint - 0.1 <= actual <= setpoint + 0.1

    If use_completion_callback is True, the completion callback must complete before
    ``set_success_func`` is ever called.

    Executing this function should be "fast" (i.e. the function should not sleep), and it should
    not do any external I/O.

    Defaults to :py:obj:`None`, which means no check is applied.
    """

    set_timeout_s: float | None = None
    """
    A timeout, in seconds, on the value being set successfully. The timeout
    applies to the EPICS completion callback (if enabled) and the set success function
    (if provided), and excludes any configured settle time.

    Defaults to :py:obj:`None`, which means no timeout.
    """

    settle_time_s: float = 0.0
    """
    A wait time, in seconds, which is unconditionally applied just before the set
    status is marked as complete. Defaults to zero.
    """

    use_global_moving_flag: bool = False
    """
    Whether to wait for the IBEX global moving indicator to return "stationary". This is useful
    for compound moves, where changing a single block may cause multiple underlying axes to
    move, and all movement needs to be complete before the set is considered complete.
    """

    timeout_is_error: bool = True
    """
    Whether a write timeout is considered an error. Defaults to True. If False, a set will be
    marked as complete without error even if the block has not given a completion callback or
    satisfied ``set_success_func`` within ``settle_time_s``.
    """


class RunControl(StandardReadable):
    """Subdevice for common run-control signals."""

    def __init__(self, prefix: str, name: str = "") -> None:
        """Subdevice for common run-control signals.

        .. note::

            Run control should be accessed via the ``run_control`` property on a block,
            rather than by constructing an instance of this class directly.

        Args:
            prefix: the run-control prefix, e.g. ``IN:INSTRUMENT:CS:SB:blockname:RC:``
            name: ophyd device name

        """
        with self.add_children_as_readables(StandardReadableFormat.HINTED_SIGNAL):
            # When explicitly reading run control, the most obvious signal that people will be
            # interested in is whether the block is in range or not.
            self.in_range: SignalR[bool] = epics_signal_r(bool, f"{prefix}INRANGE")
            """Whether run-control is currently in-range."""

        self.low_limit: SignalRW[float] = epics_signal_rw(float, f"{prefix}LOW")
        """Run-control low limit."""
        self.high_limit: SignalRW[float] = epics_signal_rw(float, f"{prefix}HIGH")
        """Run-control high limit."""

        self.suspend_if_invalid: SignalRW[bool] = epics_signal_rw(bool, f"{prefix}SOI")
        """Whether run-control should suspend data collection on invalid values."""
        self.enabled: SignalRW[bool] = epics_signal_rw(bool, f"{prefix}ENABLE")
        """Run-control enabled."""

        self.out_time: SignalR[float] = epics_signal_r(float, f"{prefix}OUT:TIME")
        """Run-control time outside limits."""
        self.in_time: SignalR[float] = epics_signal_r(float, f"{prefix}IN:TIME")
        """Run-control time inside limits."""

        super().__init__(name=name)


class BlockR(StandardReadable, Triggerable, Generic[T]):
    """Read-only block."""

    def __init__(self, datatype: type[T], prefix: str, block_name: str) -> None:
        """Device representing an IBEX readable block of arbitrary data type.

        Args:
            datatype: the type of data in this block
                (e.g. :py:obj:`str`, :py:obj:`int`, :py:obj:`float`)
            prefix: the current instrument's PV prefix
            block_name: the name of the block

        """
        with self.add_children_as_readables(StandardReadableFormat.HINTED_SIGNAL):
            self.readback: SignalR[T] = epics_signal_r(datatype, f"{prefix}CS:SB:{block_name}")
            """Readback value. This is the hinted signal for a block."""

        # Run control doesn't need to be read by default
        self.run_control: RunControl = RunControl(f"{prefix}CS:SB:{block_name}:RC:")
        """Run-control settings for this block."""

        super().__init__(name=block_name)
        self.readback.set_name(block_name)

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        """Blocks do not do anything when triggered.

        This method implements :py:obj:`bluesky.protocols.Triggerable`,
        and should not be called directly.

        This empty implementation is provided to allow using blocks in
        adaptive scans.
        """

    def __repr__(self) -> str:
        """Debug representation of this block."""
        return f"{self.__class__.__name__}(name={self.name})"


class BlockRw(BlockR[T], NamedMovable[T]):
    """Device representing an IBEX read/write block of arbitrary data type."""

    def __init__(
        self,
        datatype: type[T],
        prefix: str,
        block_name: str,
        *,
        write_config: BlockWriteConfig[T] | None = None,
        sp_suffix: str = ":SP",
    ) -> None:
        """Device representing an IBEX read/write block of arbitrary data type.

        The setpoint is not added to ``read()`` by default. For most cases where setpoint readback
        functionality is desired, :py:obj:`~ibex_bluesky_core.devices.block.BlockRwRbv` is a more
        suitable type.

        If you *explicitly* need to read the setpoint from a
        :py:obj:`~ibex_bluesky_core.devices.block.BlockRw`, you can do so in a plan with:

        .. code-block:: python

            import bluesky.plan_stubs as bps

            def plan():
                block: BlockRw = ...
                yield from bps.rd(block.setpoint)

        But note that this does not read back the setpoint from hardware, but rather the setpoint
        which was last sent by EPICS.

        Args:
            datatype: the type of data in this block (e.g. str, int, float)
            prefix: the current instrument's PV prefix
            block_name: the name of the block
            write_config: Settings which control how this device will set the underlying PVs
            sp_suffix: Suffix to append to PV for the setpoint. Defaults to ":SP" but can
                be set to empty string to read and write to exactly the same PV.

        """
        self._write_config: BlockWriteConfig[T] = write_config or BlockWriteConfig()

        self.setpoint: SignalRW[T] = epics_signal_rw(
            datatype,
            f"{prefix}CS:SB:{block_name}{sp_suffix}",
            wait=self._write_config.use_completion_callback,
        )
        """The setpoint for this block."""

        if self._write_config.use_global_moving_flag:
            # Misleading PV name... says it's a str but it's really a bi record.
            # Only link to this if we need to (i.e. if use_global_moving_flag was requested)
            self.global_moving = epics_signal_r(bool, f"{prefix}CS:MOT:MOVING:STR")

        super().__init__(datatype=datatype, prefix=prefix, block_name=block_name)

    @AsyncStatus.wrap
    async def set(self, value: T) -> None:
        """Set the setpoint of this block.

        This method implements :py:obj:`bluesky.protocols.Movable`, and should not be
        called directly.

        From a plan, set a block using:

        .. code-block:: python

            import bluesky.plan_stubs as bps

            def my_plan():
                block = BlockRw(...)
                yield from bps.mv(block, value)
        """

        async def do_set(setpoint: T) -> None:
            logger.info("Setting Block %s to %s", self.name, setpoint)
            await self.setpoint.set(setpoint, timeout=None)
            logger.info("Got completion callback from setting block %s to %s", self.name, setpoint)

            if self._write_config.use_global_moving_flag:
                logger.info(
                    "Waiting for global moving flag on setting block %s to %s", self.name, setpoint
                )
                # Paranoid sleep - ensure that the global flag has had a chance to go into moving,
                # otherwise there could be a race condition where we check the flag before the move
                # has even started.
                await asyncio.sleep(GLOBAL_MOVING_FLAG_PRE_WAIT)
                await wait_for_value(self.global_moving, False, timeout=None)
                logger.info(
                    "Done wait for global moving flag on setting block %s to %s",
                    self.name,
                    setpoint,
                )

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

        if self._write_config.timeout_is_error:
            await set_and_settle(value)
        else:
            try:
                await set_and_settle(value)
            except TimeoutError as e:
                logger.info(
                    "block set %s value=%s failed with %s, but continuing anyway because "
                    "continue_on_failed_write is set.",
                    self.name,
                    value,
                    e,
                )
        logger.info("block set complete %s value=%s", self.name, value)


class BlockRwRbv(BlockRw[T], Locatable[T]):
    """Device representing an IBEX read/write/setpoint readback block of arbitrary data type."""

    def __init__(
        self,
        datatype: type[T],
        prefix: str,
        block_name: str,
        *,
        write_config: BlockWriteConfig[T] | None = None,
    ) -> None:
        """Device representing an IBEX read/write/setpoint readback block of arbitrary data type.

        The setpoint readback is added to read(), but not hints(), by default. If you do not have
        a setpoint readback, use :py:obj:`~ibex_bluesky_core.devices.block.BlockRw` instead.

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
            """The setpoint-readback for this block."""

        super().__init__(
            datatype=datatype, prefix=prefix, block_name=block_name, write_config=write_config
        )

    async def locate(self) -> Location[T]:
        """Get the current :py:obj:`~bluesky.protocols.Location` of this block.

        This method implements :py:obj:`bluesky.protocols.Locatable`, and should not be
        called directly.

        From a plan, locate a block using:

        .. code-block:: python

            import bluesky.plan_stubs as bps

            def my_plan():
                block: BlockRwRbv = ...
                location = yield from bps.locate(block)

        If you only need the current value, rather than the value and the setpoint-readback, use:

        .. code-block:: python

            import bluesky.plan_stubs as bps

            def my_plan():
                block: BlockRwRbv = ...
                value = yield from bps.rd(block)

        """
        logger.info("locating block %s", self.name)
        actual, sp_rbv = await asyncio.gather(
            self.readback.get_value(),
            self.setpoint_readback.get_value(),
        )
        return {
            "readback": actual,
            "setpoint": sp_rbv,
        }


class BlockMot(Motor, Movable[float], HasName):
    """Device representing an IBEX block pointing at a motor."""

    def __init__(
        self,
        prefix: str,
        block_name: str,
    ) -> None:
        """Create a new motor-record block.

        The ``BlockMot`` object supports motion-specific functionality such as:

        - Stopping if a scan is aborted (supports the bluesky
          :py:obj:`~bluesky.protocols.Stoppable` protocol)
        - Limit checking (before a move starts - supports the bluesky
          :py:obj:`~bluesky.protocols.Checkable` protocol)
        - Automatic calculation of move timeouts based on motor velocity
        - Fly scanning

        However, it generally relies on the underlying motor being "well-behaved". For example, a
        motor which does many retries may exceed the simple default timeout based on velocity (it
        is possible to explicitly specify a timeout on set() to override this).

        Blocks pointing at motors do not take a
        :py:obj:`~ibex_bluesky_core.devices.block.BlockWriteConfig` parameter, as these
        parameters duplicate functionality which already exists in the motor record. The mapping is:

        ``use_completion_callback``:
            Motors always use completion callbacks to check whether motion has completed. Whether to
            wait on that completion callback can be configured by the 'wait' keyword argument on
            set().
        ``set_success_func``:
            Use ``.RDBD`` and ``.RTRY`` to control motor retries if the position has not been
            reached to within a specified tolerance. Note that motors which retry a lot may
            exceed the default motion timeout which is calculated based on velocity,
            distance and acceleration.
        ``set_timeout_s``:
            A suitable timeout is calculated automatically based on velocity, distance and
            acceleration as defined on the motor record.
        ``settle_time_s``:
            Use ``.DLY`` on the motor record to configure this.
        ``use_global_moving_flag``:
            This is unnecessary for a single motor block, as a completion callback will always be
            used instead to detect when a single move has finished.

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

    def set(  # pyright: ignore
        self, value: float, timeout: CalculatableTimeout = CALCULATE_TIMEOUT
    ) -> WatchableAsyncStatus[float]:
        """Pass through ``set`` to :py:obj:`ophyd_async.epics.motor.Motor.set`.

        This is needed so that type-checker correctly understands the type of set.

        This method will raise
        :external+ophyd_async:py:obj:`ophyd_async.epics.motor.MotorLimitsError`
        if the requested position was outside the motor's limits.
        """
        return super().set(value, timeout)


def block_r(datatype: type[T], block_name: str) -> BlockR[T]:
    """Get a local read-only block for the current instrument.

    See documentation of :py:obj:`~ibex_bluesky_core.devices.block.BlockR` for more information.
    """
    return BlockR(datatype=datatype, prefix=get_pv_prefix(), block_name=block_name)


def block_rw(
    datatype: type[T],
    block_name: str,
    *,
    write_config: BlockWriteConfig[T] | None = None,
    sp_suffix: str = ":SP",
) -> BlockRw[T]:
    """Get a local read-write block for the current instrument.

    See documentation of :py:obj:`~ibex_bluesky_core.devices.block.BlockRw` for more information.
    """
    return BlockRw(
        datatype=datatype,
        prefix=get_pv_prefix(),
        block_name=block_name,
        write_config=write_config,
        sp_suffix=sp_suffix,
    )


def block_w(
    datatype: type[T], block_name: str, *, write_config: BlockWriteConfig[T] | None = None
) -> BlockRw[T]:
    """Get a write-only block for the current instrument.

    This is a :py:obj:`~ibex_bluesky_core.devices.block.BlockRw` instance with no SP suffix.
    """
    return BlockRw(
        datatype=datatype,
        prefix=get_pv_prefix(),
        block_name=block_name,
        write_config=write_config,
        sp_suffix="",
    )


def block_rw_rbv(
    datatype: type[T], block_name: str, *, write_config: BlockWriteConfig[T] | None = None
) -> BlockRwRbv[T]:
    """Get a local read/write/setpoint readback block for the current instrument.

    See documentation of :py:obj:`~ibex_bluesky_core.devices.block.BlockRwRbv` for more information.
    """
    return BlockRwRbv(
        datatype=datatype, prefix=get_pv_prefix(), block_name=block_name, write_config=write_config
    )


def block_mot(block_name: str) -> BlockMot:
    """Get a local block pointing at a motor record for the local instrument.

    See documentation of :py:obj:`~ibex_bluesky_core.devices.block.BlockMot` for more information.
    """
    return BlockMot(prefix=get_pv_prefix(), block_name=block_name)
