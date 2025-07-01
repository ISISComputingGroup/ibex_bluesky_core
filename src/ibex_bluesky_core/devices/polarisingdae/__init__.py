"""An interface to the DAE for bluesky, suited for polarisation."""

import logging
from typing import Generic, TypeAlias

import scipp as sc
from bluesky.protocols import Movable, Triggerable
from ophyd_async.core import (
    AsyncStageable,
    AsyncStatus,
    Reference,
)
from typing_extensions import TypeVar

from ibex_bluesky_core.devices.dae import Dae
from ibex_bluesky_core.devices.polarisingdae._reducers import (
    MultiWavelengthBandNormalizer,
    PolarisationReducer,
)
from ibex_bluesky_core.devices.simpledae import (
    Controller,
    GoodFramesWaiter,
    PeriodGoodFramesWaiter,
    PeriodPerPointController,
    Reducer,
    RunPerPointController,
    Waiter,
    wavelength_bounded_spectra,
)
from ibex_bluesky_core.utils import get_pv_prefix

logger = logging.getLogger(__name__)

__all__ = [
    "DualRunDae",
    "MultiWavelengthBandNormalizer",
    "PolarisationReducer",
    "polarising_dae",
]

TController_co = TypeVar("TController_co", bound="Controller", default=Controller, covariant=True)
TWaiter_co = TypeVar("TWaiter_co", bound="Waiter", default=Waiter, covariant=True)
TPReducer_co = TypeVar(
    "TPReducer_co",
    bound="Reducer",
    default=Reducer,
    covariant=True,
)
TMWBReducer_co = TypeVar(
    "TMWBReducer_co",
    bound="Reducer",
    default=Reducer,
    covariant=True,
)


class DualRunDae(
    Dae,
    Triggerable,
    AsyncStageable,
    Generic[TController_co, TWaiter_co, TPReducer_co, TMWBReducer_co],
):
    """DAE with strategies for data collection, waiting, and reduction, suited for polarisation.

    This class is a more complex version of SimpleDae. It requires a flipper device to be provided
    and will perform two runs, changing the flipper device at the start and inbetween runs.
    """

    def __init__(  # noqa: PLR0913
        self,
        *,
        prefix: str,
        name: str = "DAE",
        controller: TController_co,
        waiter: TWaiter_co,
        reducer_final: TPReducer_co,
        reducer_up: TMWBReducer_co,
        reducer_down: TMWBReducer_co,
        flipper: Movable[float],
        flipper_states: list[float],
    ) -> None:
        """Initialise a DualRunDae.

        Args:
            prefix: the PV prefix of the instrument being controlled.
            name: A friendly name for this DAE object.
            controller: A DAE control strategy, defines how the DAE begins and ends data acquisition
                Pre-defined strategies in the ibex_bluesky_core.devices.controllers module
            waiter: A waiting strategy, defines how the DAE waits for an acquisition to be complete
                Pre-defined strategies in the ibex_bluesky_core.devices.waiters module
            reducer_final: A data reduction strategy. It will be triggered once after the two runs.
            reducer_up: A data reduction strategy. Triggers once after the first run completes.
            reducer_down: A data reduction strategy. Triggers once after the second run completes.
            flipper: A device which will be changed at the start of the first run and between runs.
            flipper_states: A tuple of two floats, the states to set at the start and between runs.

        """
        self.flipper: Reference[Movable[float]] = Reference(flipper)
        self.flipper_states: list[float] = flipper_states

        self._prefix = prefix
        self.controller: TController_co = controller
        self.waiter: TWaiter_co = waiter
        self.reducer_up: TMWBReducer_co = reducer_up
        self.reducer_down: TMWBReducer_co = reducer_down
        self.reducer_final: TPReducer_co = reducer_final

        logger.info(
            """created polarisingdae with prefix=%s, controller=%s,
             waiter=%s, reducer=%s, reducer_up=%s, reducer_down=%s""",
            prefix,
            controller,
            waiter,
            reducer_final,
            reducer_up,
            reducer_down,
        )

        # controller, waiter and reducers may be Devices (but don't necessarily have to be),
        # so can define their own signals. do __init__ after defining those, so that the signals
        # are connected/named and usable.
        super().__init__(prefix=prefix, name=name)

        # Ask each defined strategy what it's interesting signals are, and ensure those signals are
        # published when the top-level SimpleDae object is read.
        extra_readables = set()
        for strategy in [
            self.controller,
            self.waiter,
            self.reducer_up,
            self.reducer_down,
            self.reducer_final,
        ]:
            extra_readables.update(strategy.additional_readable_signals(self))
        logger.info("extra readables: %s", list(extra_readables))
        self.add_readables(devices=list(extra_readables))

    @AsyncStatus.wrap
    async def stage(self) -> None:
        """Pre-scan setup. Delegate to the controller."""
        await self.controller.setup(self)

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        """Take a single measurement and prepare it for later reading.

        This waits for the acquisition and any defined reduction to be complete, such that
        after this coroutine completes, all relevant data is available via read()
        """
        self.flipper().set(self.flipper_states[0])

        await self.controller.start_counting(self)
        await self.waiter.wait(self)
        await self.controller.stop_counting(self)
        await self.reducer_up.reduce_data(self)

        self.flipper().set(self.flipper_states[1])

        await self.controller.start_counting(self)
        await self.waiter.wait(self)
        await self.controller.stop_counting(self)
        await self.reducer_down.reduce_data(self)

        await self.reducer_final.reduce_data(self)

    @AsyncStatus.wrap
    async def unstage(self) -> None:
        """Post-scan teardown, delegate to the controller."""
        await self.controller.teardown(self)


PolarisingDualRunDae: TypeAlias = DualRunDae[
    Controller, Waiter, PolarisationReducer, MultiWavelengthBandNormalizer
]


def polarising_dae(  # noqa: PLR0913
    *,
    det_pixels: list[int],
    frames: int,
    flipper: Movable[float],
    flipper_states: list[float],
    intervals: list[sc.Variable],
    total_flight_path_length: sc.Variable,
    periods: bool = True,
    monitor: int = 1,
    save_run: bool = False,
) -> PolarisingDualRunDae:
    """Create a Polarising DAE which uses wavelength binning and calculates polarisation.

    This is a different version of monitor_normalising_dae, with a more complex set of strategies.
    While already normalising using a monitor and waiting for frames, it requires a flipper device
    to be provided and will change the flipper between two neutron states between runs. It uses
    wavelength-bounded binning, and on completion of the two runs will calculate polarisation.

    Args:
        det_pixels: list of detector pixel to use for scanning.
        frames: number of frames to wait for.
        flipper: A device which can be used to change the neutron state between runs.
        flipper_states: A tuple of two floats, the neutron states to be set between runs.
        intervals: list of wavelength intervals to use for binning.
        total_flight_path_length: total flight path length of the neutron beam
            from monitor to detector.
        periods: whether or not to use software periods.
        monitor: the monitor spectra number.
        save_run: whether or not to save the run of the DAE.

    """
    prefix = get_pv_prefix()

    if periods:
        controller = PeriodPerPointController(save_run=save_run)
        waiter = PeriodGoodFramesWaiter(frames)
    else:
        controller = RunPerPointController(save_run=save_run)
        waiter = GoodFramesWaiter(frames)

    sum_wavelength_bands = [
        wavelength_bounded_spectra(bounds=i, total_flight_path_length=total_flight_path_length)
        for i in intervals
    ]

    reducer_up = MultiWavelengthBandNormalizer(
        prefix=prefix,
        detector_spectra=det_pixels,
        monitor_spectra=[monitor],
        sum_wavelength_bands=sum_wavelength_bands,
    )

    reducer_down = MultiWavelengthBandNormalizer(
        prefix=prefix,
        detector_spectra=det_pixels,
        monitor_spectra=[monitor],
        sum_wavelength_bands=sum_wavelength_bands,
    )

    reducer_final = PolarisationReducer(
        intervals=intervals, reducer_up=reducer_up, reducer_down=reducer_down
    )

    dae = DualRunDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer_final=reducer_final,
        reducer_up=reducer_up,
        reducer_down=reducer_down,
        flipper=flipper,
        flipper_states=flipper_states,
    )

    return dae
