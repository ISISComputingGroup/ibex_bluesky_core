"""Plans specific to Reflectometry beamlines."""

from collections.abc import Generator

from bluesky import Msg

from ibex_bluesky_core.callbacks import FitMethod, ISISCallbacks
from ibex_bluesky_core.devices.reflectometry import refl_parameter
from ibex_bluesky_core.devices.simpledae import monitor_normalising_dae
from ibex_bluesky_core.plans import (
    adaptive_scan,
    scan,
)
from ibex_bluesky_core.plans.reflectometry._autoalign import optimise_axis_against_intensity
from ibex_bluesky_core.plans.reflectometry._det_map_align import (
    DetMapAlignResult,
    angle_scan_plan,
    height_and_angle_scan_plan,
)
from ibex_bluesky_core.utils import centred_pixel

__all__ = [
    "DetMapAlignResult",
    "angle_scan_plan",
    "height_and_angle_scan_plan",
    "optimise_axis_against_intensity",
    "refl_adaptive_scan",
    "refl_scan",
]


def refl_scan(  # noqa: PLR0913
    param: str,
    start: float,
    stop: float,
    num: int,
    *,
    frames: int,
    det: int,
    mon: int,
    model: FitMethod,
    pixel_range: int = 0,
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
        num: the number of points to scan.
        frames: the number of frames to wait for.
        det: the detector spectra to use.
        mon: the monitor spectra to use.
        pixel_range: the range of pixels to scan over, using `det` as a centred pixel.
        model: the model to use.
        periods: whether to use periods.
        save_run: whether to save the run of the scan.
        rel: whether to use a relative scan around the current position.

    Returns:
        an :obj:`ibex_bluesky_core.callbacks.ISISCallbacks` instance.

    """
    block = refl_parameter(param)
    det_pixels = centred_pixel(det, pixel_range)
    dae = monitor_normalising_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    )

    return (
        yield from scan(
            dae=dae,
            block=block,
            start=start,
            stop=stop,
            num=num,
            model=model,
            save_run=save_run,
            periods=periods,
            rel=rel,
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
    det: int,
    mon: int,
    model: FitMethod,
    pixel_range: int = 0,
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

    Returns:
        an :obj:`ibex_bluesky_core.callbacks.ISISCallbacks` instance.

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
