"""DAE control strategies."""

import logging
import typing

from ophyd_async.core import (
    Device,
    StandardReadable,
    soft_signal_r_and_setter,
    wait_for_value,
)

from ibex_bluesky_core.devices.dae.dae import RunstateEnum
from ibex_bluesky_core.devices.dae.dae_controls import BeginRunExBits
from ibex_bluesky_core.devices.simpledae.strategies import Controller

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from ibex_bluesky_core.devices.simpledae import SimpleDae


async def _end_or_abort_run(dae: "SimpleDae", save: bool) -> None:
    if save:
        logger.info("ending run")
        await dae.controls.end_run.trigger(wait=True, timeout=None)
        logger.info("run ended")
    else:
        logger.info("aborting run")
        await dae.controls.abort_run.trigger(wait=True, timeout=None)
        logger.info("run aborted")


class PeriodPerPointController(Controller):
    """Controller for a SimpleDae which counts using a period per point.

    A single run is opened during stage(), and then each new point will count into a new
    DAE period (starting from 1). The run will be either ended or aborted in unstage, depending
    on the value of the save_run parameter.
    """

    def __init__(self, save_run: bool) -> None:
        """Period-per-point DAE controller.

        Args:
            save_run: True to terminate runs using end(), saving the data. False to terminate runs
                using abort(), discarding the data.

        """
        self._save_run = save_run
        self._current_period = 0

    async def setup(self, dae: "SimpleDae") -> None:
        """Pre-scan setup (begin a new run in paused mode)."""
        self._current_period = 0
        logger.info("setting up new run")
        await dae.controls.begin_run_ex.set(BeginRunExBits.BEGIN_PAUSED)
        await wait_for_value(dae.run_state, RunstateEnum.PAUSED, timeout=10)
        logger.info("setup complete")

    async def start_counting(self, dae: "SimpleDae") -> None:
        """Start counting a scan point.

        Increments the period by 1, then unpauses the run.
        """
        logger.info("start counting")
        self._current_period += 1
        await dae.period_num.set(self._current_period, wait=True, timeout=None)

        # Error if the period change didn't work (e.g. we have exceeded max periods)
        await wait_for_value(
            dae.period_num,
            self._current_period,
            timeout=10,
        )

        # Ensure frame counters have reset to zero for the new period.
        logger.info("waiting for frame counters to be zero")
        await wait_for_value(dae.period.good_frames, 0, timeout=10)
        await wait_for_value(dae.period.raw_frames, 0, timeout=10)

        logger.info("resuming run")
        await dae.controls.resume_run.trigger(wait=True, timeout=None)
        await wait_for_value(
            dae.run_state,
            lambda v: v in [RunstateEnum.RUNNING, RunstateEnum.WAITING, RunstateEnum.VETOING],
            timeout=10,
        )

    async def stop_counting(self, dae: "SimpleDae") -> None:
        """Stop counting a scan point, by pausing the run."""
        logger.info("stop counting")
        await dae.controls.pause_run.trigger(wait=True, timeout=None)
        await wait_for_value(dae.run_state, RunstateEnum.PAUSED, timeout=10)

    async def teardown(self, dae: "SimpleDae") -> None:
        """Finish taking data, ending or aborting the run."""
        await _end_or_abort_run(dae, self._save_run)

    def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
        """period_num is always an interesting signal if using this controller."""
        return [dae.period_num]


class RunPerPointController(Controller, StandardReadable):
    """Controller for a SimpleDae which counts using a DAE run per point.

    The runs can be either ended or aborted once counting is finished.

    """

    def __init__(self, save_run: bool) -> None:
        """Init.

        Args:
            save_run: whether to end the run (True) or abort the run (False) on completion.

        """
        self._save_run = save_run

        # This run number is the run that the DAE *actually* counted into, as opposed to reading
        # dae.run_number, which increments immediately after end and so reflects the next run
        # number.
        self.run_number, self._run_number_setter = soft_signal_r_and_setter(int, 0)
        super().__init__()

    async def start_counting(self, dae: "SimpleDae") -> None:
        """Start counting a scan point, by starting a DAE run."""
        logger.info("start counting")
        await dae.controls.begin_run.trigger(wait=True, timeout=None)
        await wait_for_value(
            dae.run_state,
            lambda v: v in [RunstateEnum.RUNNING, RunstateEnum.WAITING, RunstateEnum.VETOING],
            timeout=10,
        )

        # Take care to read this after we've started a run, but before ending it, so that it
        # accurately reflects the run number we're actually counting into.
        logger.info("saving current run number")
        run_number = await dae.current_or_next_run_number.get_value()
        self._run_number_setter(run_number)

    async def stop_counting(self, dae: "SimpleDae") -> None:
        """Stop counting a scan point, by ending or aborting the run."""
        await _end_or_abort_run(dae, self._save_run)

    def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
        """Run number is an interesting signal only if saving runs."""
        if self._save_run:
            return [self.run_number]
        else:
            return []
