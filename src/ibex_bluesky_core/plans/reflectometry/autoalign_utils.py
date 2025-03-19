"""A general tool for reflectometers to use to save time aligning their beamlines."""

from collections.abc import Generator
from typing import Callable, Tuple

import bluesky.plan_stubs as bps
from bluesky.protocols import NamedMovable
from bluesky.utils import Msg
from lmfit.model import ModelResult
from typing_extensions import NotRequired, TypedDict, Unpack

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.callbacks.fitting import FitMethod
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.plan_stubs import call_sync
from ibex_bluesky_core.plans import scan


def _check_parameter(
    alignment_param_value: float,
    result: ModelResult,
    init_mot_pos: float,
    rel_scan_range: float,
    is_good_fit: Callable[[ModelResult, float], bool] | None = None,
) -> bool:
    """Check that the optimised value is within scan range and then runs user provided checks.

    Returns True means the found result was sensible.

    Args:
        alignment_param_value (float): The name of the optimised value.
        result (ModelResult): The fitting resuls returned from lmfit.
        init_mot_pos (float): The initial motor position before scanning.
        rel_scan_range (float): The current relative scan range.
        user_checks (Callable[[ModelResult, float], bool] | None): User provided checks on the
            optimised value, must return True if result is sensible.

    Returns:
        True if value is not sensible. False otherwise.

    """
    if init_mot_pos + rel_scan_range < alignment_param_value:
        return False

    elif init_mot_pos - rel_scan_range > alignment_param_value:
        return False

    if is_good_fit is None:
        return True

    return is_good_fit(result, alignment_param_value)


def _get_alignment_param_value(icc: ISISCallbacks, fit_param: str) -> float:
    return icc.live_fit.result.values[fit_param]


def _inner_loop(
    dae: SimpleDae,
    fit_param: str,
    alignment_param: NamedMovable[float],
    rel_scan_range: float,
    num_points: int,
    fit_method: FitMethod,
    periods: bool,
    save_run: bool,
    is_good_fit: Callable[[ModelResult, float], bool] | None,
    problem_found_plan: Callable[[], Generator[Msg, None, None]],
) -> Generator[Msg, None, Tuple[ISISCallbacks, bool]]:
    """Functionality to perform on a per scan basis.

    Args:
        icc (ISISCallbacks): ISIS Callback Collection object.
        dae (SimpleDae): A readable DAE object.
        alignment_param (AlignmentParam): The alignment parameter to be scanned over and optimised.
        rel_scan_range (float): The current relative scan range.
        num_points (int): The number of points across the scan.
        problem_found_plan (Callable[[], Generator[Msg, None, None]] | None]):
            A callback for what to do if the optimised value is not found to be sensible.

    Returns:
        Whether there was a problem during runtime. Returns True if there was. (bool).

    """
    print(f"Scanning over {alignment_param.name} with a relative scan range of {rel_scan_range}.")

    init_mot_pos: float = yield from bps.rd(alignment_param)  # type: ignore

    def _inner() -> Generator[Msg, None, ISISCallbacks]:
        icc = yield from scan(
            dae=dae,
            block=alignment_param,
            start=-rel_scan_range / 2,
            stop=rel_scan_range / 2,
            num=num_points,
            model=fit_method,
            periods=periods,
            save_run=save_run,
            rel=True,
        )

        return icc

    icc = yield from _inner()

    alignment_param_value = _get_alignment_param_value(icc, fit_param)

    if not _check_parameter(
        alignment_param_value=alignment_param_value,
        result=icc.live_fit.result,
        init_mot_pos=init_mot_pos,
        rel_scan_range=rel_scan_range,
        is_good_fit=is_good_fit,
    ):
        print(
            f"""This failed one or more of the checks on {alignment_param.name}"""
            f""" with a scan range of {rel_scan_range}."""
        )
        print(f"Value found for {fit_param} was {alignment_param_value}.")

        yield from problem_found_plan()

        def inp() -> Generator[Msg, None, str]:
            choice = yield from call_sync(
                input,
                """Type '1' if you would like to re-scan or type '2' to re-zero"""
                f""" at {alignment_param_value} and keep going.""",
            )

            if choice not in {"1", "2"}:
                choice = yield from inp()

            return choice

        choice = yield from inp()
        if choice == "1":
            return (icc, True)

    print(f"Moving {alignment_param.name} to {alignment_param_value}.")
    yield from bps.mv(alignment_param, alignment_param_value)  # type: ignore

    return (icc, False)


class OptimiseAxisParams(TypedDict):
    """Type hints for optimise_axis_against_intensity."""

    num_points: NotRequired[int]
    periods: NotRequired[bool]
    save_run: NotRequired[bool]
    problem_found_plan: NotRequired[Callable[[], Generator[Msg, None, None]]]
    is_good_fit: NotRequired[Callable[[ModelResult, float], bool] | None]


def optimise_axis_against_intensity(  # noqa # D417
    dae: SimpleDae,
    alignment_param: NamedMovable[float],
    fit_method: FitMethod,
    fit_param: str,
    rel_scan_ranges: list[float],
    **kwargs: Unpack[OptimiseAxisParams],
) -> Generator[Msg, None, ISISCallbacks | None]:
    """Optimise a motor/device to the intensity of the beam.

    Scan between two symmetrical points relative to alignment_param's current motor position,
    to find where the optimal point is depending on alignment_param.fit_param, move to it and
    redefine as zero, then optionally repeat the process for a smaller range and higher
    granularity.

    Args:
        dae (SimpleDae): A readable signal that represents beam intensity.
        alignment_param (AlignmentParam): The alignment parameter to be scanned over and optimised.

    Keyword Args:
        num_points (int): The number of points across the scan. Defaults to 10.
        periods (bool): Are DAE periods being used. Defaults to True.
        save_run (bool): Should runs be saved. Defaults to True.
        problem_found_plan (Callable[[], Generator[Msg, None, None]] | None):
            A plan, called if optimised value is not found to be
            sensible.

    Returns:
        Instance of :obj:`ibex_bluesky_core.callbacks.ISISCallbacks`.

    """
    num_points = kwargs.get("num_points", 10)
    periods = kwargs.get("periods", True)
    save_run = kwargs.get("save_run", True)
    problem_found_plan = kwargs.get("problem_found_plan", bps.null)
    is_good_fit = kwargs.get("is_good_fit", None)

    while True:  # If a problem is found, then start the alignment again
        problem_found = False
        icc = None

        for rel_scan_range in rel_scan_ranges:
            (icc, problem_found) = yield from _inner_loop(
                dae=dae,
                alignment_param=alignment_param,
                rel_scan_range=rel_scan_range,
                num_points=num_points,
                is_good_fit=is_good_fit,
                fit_param=fit_param,
                problem_found_plan=problem_found_plan,
                fit_method=fit_method,
                periods=periods,
                save_run=save_run,
            )

            if problem_found:
                break

        if not problem_found:
            return icc
