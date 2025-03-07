"""Plans specific to Reflectometry beamlines."""

from collections.abc import Generator

from bluesky import Msg

from ibex_bluesky_core.callbacks import FitMethod, ISISCallbacks
from ibex_bluesky_core.devices.reflectometry import refl_parameter
from ibex_bluesky_core.devices.simpledae import monitor_normalising_dae
from ibex_bluesky_core.plans import (
    DEFAULT_DET,
    DEFAULT_FIT_METHOD,
    DEFAULT_MON,
    adaptive_scan,
    scan,
)
from ibex_bluesky_core.utils import centred_pixel


def refl_scan(  # noqa: PLR0913
    param: str,
    start: float,
    stop: float,
    count: int,
    *,
    frames: int,
    det: int = DEFAULT_DET,
    mon: int = DEFAULT_MON,
    pixel_range: int = 0,
    model: FitMethod = DEFAULT_FIT_METHOD,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
) -> Generator[Msg, None, ISISCallbacks]:
    """Scan over a reflectometry parameter.

    This is really just a wrapper around :func:`ibex_bluesky_core.plans.scan`

    Args:
        param: the reflectometry parameter.
        start: the starting setpoint of the parameter.
        stop: the final setpoint of the parameter.
        count: the number of points to scan.
        frames: the number of frames to wait for.
        det: the detector spectra to use.
        mon: the monitor spectra to use.
        pixel_range: the range of pixels to scan over, using `det` as a centred pixel.
        model: the model to use.
        periods: whether to use periods.
        save_run: whether to save the run of the scan.
        rel: whether to use a relative scan around the current position.

    """
    block = refl_parameter(param)
    det_pixels = centred_pixel(det, pixel_range)
    dae = monitor_normalising_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    )

    return (
        yield from scan(
            dae, block, start, stop, count, model=model, save_run=save_run, periods=periods, rel=rel
        )
    )


def refl_adaptive_scan(  # noqa: PLR0913
    param: str,
    start: float,
    stop: float,
    min_step: float,
    max_step: float,
    target_delta: float,
    *,
    frames: int,
    det: int = DEFAULT_DET,
    mon: int = DEFAULT_MON,
    pixel_range: int = 0,
    model: FitMethod = DEFAULT_FIT_METHOD,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
) -> Generator[Msg, None, ISISCallbacks]:
    """Perform an adaptive scan over a reflectometry parameter.

    This is really just a wrapper around :func:`ibex_bluesky_core.plans.adaptive_scan`

    Args:
        param: The parameter to scan.
        start: The initial setpoint.
        stop: The final setpoint.
        min_step: the minimum step size to plot
        max_step: the maximum step size to plot
        target_delta: desired fractional change in detector signal between steps
        frames: the number of frames to wait for.
        det: the detector spectra to use.
        mon: the monitor spectra to use.
        pixel_range: the range of pixels to scan over, using `det` as a centred pixel.
        model: the fit method to use.
        periods: whether to use periods.
        save_run: whether to save the run of the scan.
        rel: whether to use a relative scan around the current position.

    """
    block = refl_parameter(param)
    det_pixels = centred_pixel(det, pixel_range)
    dae = monitor_normalising_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    )

    return (
        yield from adaptive_scan(
            dae=dae,
            block=block,
            start=start,
            stop=stop,
            min_step=min_step,
            max_step=max_step,
            target_delta=target_delta,
            model=model,
            save_run=save_run,
            rel=rel,
        )
    )
