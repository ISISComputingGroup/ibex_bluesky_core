"""Reflectometry plans and helpers."""

from collections.abc import Generator

from bluesky import Msg
from bluesky import plans as bp
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import FitMethod, ISISCallbacks
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import BlockRw, BlockWriteConfig, block_rw
from ibex_bluesky_core.devices.reflectometry.refl_param import ReflParameter
from ibex_bluesky_core.plans import common_dae, set_num_periods
from ibex_bluesky_core.run_engine import get_run_engine


def centred_pixel(centre: int, pixel_range: int) -> list[int]:
    """Given a centre and range, return a contiguous range of pixels around the centre, inclusive.

    ie. a centre of 50 with a range of 3 will give [47, 48, 49, 50, 51, 52, 53]

    Args:
          centre (int): The centre pixel number.
          pixel_range (int): The range of pixels either side to surround the centre.

    Returns a list of pixel numbers.

    """
    return [s for s in range(centre - pixel_range, centre + pixel_range + 1)]


def motor_with_tolerance(name: str, tolerance: float) -> BlockRw[float]:
    """Create a motor block with a settle time and tolerance to wait for before motion is complete.

    Args:
        name (str): The motor PV.
        tolerance (float): The motor tolerance to get to before a move is considered complete.

    Returns A device pointing to a motor.

    """

    def check(setpoint: float, actual: float) -> bool:
        return setpoint - tolerance <= actual <= setpoint + tolerance

    return block_rw(
        float,
        name,
        write_config=BlockWriteConfig(
            set_success_func=check, set_timeout_s=30.0, settle_time_s=0.5
        ),
    )


def refl_parameter(name: str) -> ReflParameter:
    """Small wrapper around a reflectometry parameter device.

    This automatically applies the current instrument's PV prefix.

    Args:
        name: the reflectometry parameter name.

    Returns a device pointing to a reflectometry parameter.

    """
    prefix = get_pv_prefix()
    return ReflParameter(prefix=prefix, name=name)


RE = get_run_engine()
DEFAULT_DET = 3
DEFAULT_MON = 1
LINEAR_FIT = Linear().fit()


def scan(  # noqa: PLR0913
    param: str,
    start: float,
    stop: float,
    count: int,
    *,
    frames: int,
    det: int = DEFAULT_DET,
    mon: int = DEFAULT_MON,
    pixel_range: int = 0,
    model: FitMethod = LINEAR_FIT,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
) -> Generator[Msg, None, None]:
    """Scan over a reflectometry parameter.

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
    dae = common_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    )

    yield from ensure_connected(dae, block)

    yield from set_num_periods(dae, count if periods else 1)

    fields = [block.name]
    if periods:
        fields.append(dae.period_num.name)  # type: ignore
    elif save_run:
        fields.append(dae.controller.run_number.name)  # type: ignore

    fields.extend(
        [
            dae.reducer.intensity.name,  # type: ignore
            dae.reducer.intensity_stddev.name,  # type: ignore
        ]
    )

    icc = ISISCallbacks(
        y=dae.reducer.intensity.name,  # type: ignore
        yerr=dae.reducer.intensity_stddev.name,  # type: ignore
        x=block.name,
        live_fit_logger_postfix="fit_2",
        measured_fields=fields,
        fit=model,
    )

    @icc
    def _inner() -> Generator[Msg, None, None]:
        if rel:
            plan = bp.rel_scan
        else:
            plan = bp.scan
        yield from plan([dae], block, start, stop, num=count)

    yield from _inner()

    if icc.live_fit.result is not None:
        print(icc.live_fit.result.fit_report())
        return icc.live_fit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None


def adaptive_scan(  # noqa: PLR0913
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
    model: FitMethod = LINEAR_FIT,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
) -> Generator[Msg, None, None]:
    """Perform an adaptive scan over a reflectometry parameter.

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
        pixel_range: the range of pixels to scan.
        model: the fit method to use.
        periods: whether to use periods.
        save_run: whether to save the run of the scan.
        rel: whether to use a relative scan around the current position.

    """
    block = refl_parameter(param)
    det_pixels = centred_pixel(det, pixel_range)
    dae = common_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    )

    yield from ensure_connected(dae, block)

    yield from set_num_periods(dae, 100)

    fields = [block.name]
    if periods:
        fields.append(dae.period_num.name)  # type: ignore
    elif save_run:
        fields.append(dae.controller.run_number.name)  # type: ignore

    fields.extend(
        [
            dae.reducer.intensity.name,  # type: ignore
            dae.reducer.intensity_stddev.name,  # type: ignore
        ]
    )

    icc = ISISCallbacks(
        y=dae.reducer.intensity.name,  # type: ignore
        yerr=dae.reducer.intensity_stddev.name,  # type: ignore
        x=block.name,
        live_fit_logger_postfix="fit_1",
        measured_fields=fields,
        fit=model,
    )

    @icc
    def _inner() -> Generator[Msg, None, None]:
        if rel:
            plan = bp.rel_adaptive_scan
        else:
            plan = bp.adaptive_scan
        yield from plan(
            [dae],
            dae.reducer.intensity.name,
            block,
            start,
            stop,
            min_step,
            max_step,
            target_delta,
            backstep=True,
        )  # type: ignore

    yield from _inner()
    if icc.live_fit.result is not None:
        print(icc.live_fit.result.fit_report())
        return icc.live_fit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None
