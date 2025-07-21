from ibex_bluesky_core.devices.dae import Dae, TimeRegimeMode
from bluesky.plans import scan
from ibex_bluesky_core.plans.time_channels_wrapper import tcb_wrapper
from ibex_bluesky_core.devices.simpledae import (
    GoodFramesNormalizer,
    GoodFramesWaiter,
    RunPerPointController,
    SimpleDae,
)
from ibex_bluesky_core.utils import get_pv_prefix
from ibex_bluesky_core.devices.block import block_rw_rbv

def test_tcb_wrapper_runs():

    prefix = get_pv_prefix()

    controller = RunPerPointController(save_run=True)
    waiter = GoodFramesWaiter(500)
    reducer = GoodFramesNormalizer(
        prefix=prefix,
        detector_spectra=[i for i in range(1, 100)],
    )

    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )
    wrapped_plan = tcb_wrapper(
        scan,
        dae,
        from_=9,
        to=87,
        steps=2,
        mode=TimeRegimeMode.DT
    )

    list(wrapped_plan)  # Forces execution

    # If no exception occurs, test passes
    assert True
