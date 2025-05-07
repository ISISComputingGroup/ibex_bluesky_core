import logging
from bluesky.protocols import NamedMovable
from ophyd_async.core import (
    AsyncStatus,
    Reference,
)
from typing_extensions import TypeVar
import scipp as sc
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.polarisingdae._reducers import PolarisingReducer, WavelengthBoundedNormalizer
from ibex_bluesky_core.devices.simpledae._controllers import (
    PeriodPerPointController,
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae._strategies import (
    Controller,
    Reducer,
    Waiter,
)
from ibex_bluesky_core.devices.simpledae._waiters import (
    GoodFramesWaiter,
    PeriodGoodFramesWaiter,
)
from ibex_bluesky_core.utils import get_pv_prefix

logger = logging.getLogger(__name__)
    

TController_co = TypeVar("TController_co", bound="Controller", default="Controller", covariant=True)
TWaiter_co = TypeVar("TWaiter_co", bound="Waiter", default="Waiter", covariant=True)
TReducer_co = TypeVar("TReducer_co", bound="Reducer", default="Reducer", covariant=True)
TPolariser_co = TypeVar("TPolariser_co", bound="PolarisingReducer", default="PolarisingReducer", covariant=True)

class PolarisingDae(SimpleDae):

    def __init__(
        self,
        *,
        prefix: str,
        name: str = "DAE",
        controller: TController_co,
        waiter: TWaiter_co,
        reducer_up: TReducer_co,
        reducer_down: TReducer_co,
        reducer: TPolariser_co,
        flipper: NamedMovable,
        flipper_states: tuple[float, float]
    ) -> None:
        
        self.flipper: Reference[NamedMovable] = Reference(flipper)
        self.flipper_states: tuple[float, float] = flipper_states
        
        self._prefix = prefix
        self.controller: TController_co = controller
        self.waiter: TWaiter_co = waiter
        self.reducer_up: TReducer_co = reducer_up
        self.reducer_down: TReducer_co = reducer_down
        self.reducer: TPolariser_co = reducer

        logger.info(
            "created polarisingdae with prefix=%s, controller=%s, waiter=%s, reducer_up=%s, reducer_down=%s, polariser=%s",
            prefix,
            controller,
            waiter,
            reducer_up,
            reducer_down,
            reducer
        )

        # controller, waiter and reducers may be Devices (but don't necessarily have to be),
        # so can define their own signals. Do __init__ after defining those, so that the signals
        # are connected/named and usable.
        super(SimpleDae, self).__init__(prefix=prefix, name=name)

        # Ask each defined strategy what it's interesting signals are, and ensure those signals are
        # published when the top-level SimpleDae object is read.
        extra_readables = set()
        for strategy in [self.controller, self.waiter, self.reducer_up, self.reducer_down, self.reducer]:
            extra_readables.update(strategy.additional_readable_signals(self))
        logger.info("extra readables: %s", list(extra_readables))
        self.add_readables(devices=list(extra_readables))

    
    @AsyncStatus.wrap
    async def trigger(self) -> None:
        """Take a single measurement and prepare it for subsequent reading.

        This waits for the acquisition and any defined reduction to be complete, such that
        after this coroutine completes all relevant data is available via read()
        """

        await self.flipper().set(self.flipper_states[0])

        await self.controller.start_counting(self)
        await self.waiter.wait(self)
        await self.controller.stop_counting(self)
        await self.reducer_up.reduce_data(self)

        await self.flipper().set(self.flipper_states[1])

        await self.controller.start_counting(self)
        await self.waiter.wait(self)
        await self.controller.stop_counting(self)
        await self.reducer_down.reduce_data(self)

        await self.reducer.reduce_data(self)

def monitor_normalising_polarising_dae(
    det_pixels: list[int],
    frames: int,
    flipper: NamedMovable,
    flipper_states: tuple[float, float],
    intervals: list[sc.Variable],
    total_flight_path_length: sc.Variable,
    periods: bool = True,
    monitor: int = 1,
    save_run: bool = False,
) -> PolarisingDae:
    
    prefix = get_pv_prefix()

    if periods:
        controller = PeriodPerPointController(save_run=save_run)
        waiter = PeriodGoodFramesWaiter(frames)
    else:
        controller = RunPerPointController(save_run=save_run)
        waiter = GoodFramesWaiter(frames)

    reducer_up = WavelengthBoundedNormalizer(
        prefix=prefix,
        detector_spectra=det_pixels,
        monitor_spectra=[monitor],
        intervals=intervals,
        total_flight_path_length=total_flight_path_length
    )

    reducer_down = WavelengthBoundedNormalizer(
        prefix=prefix,
        detector_spectra=det_pixels,
        monitor_spectra=[monitor],
        intervals=intervals,
        total_flight_path_length=total_flight_path_length
    )

    reducer = PolarisingReducer(intervals=intervals)

    dae = PolarisingDae(prefix=prefix, controller=controller, waiter=waiter, reducer_up=reducer_up, reducer_down=reducer_down, reducer=reducer, flipper=flipper, flipper_states=flipper_states)
    return dae