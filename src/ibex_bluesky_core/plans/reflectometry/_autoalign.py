"""A general tool for reflectometers to use to save time aligning their beamlines."""

import logging
from collections.abc import Callable, Generator

import bluesky.plan_stubs as bps
from bluesky.protocols import NamedMovable
from bluesky.utils import Msg
from lmfit.model import ModelResult

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.fitting import FitMethod
from ibex_bluesky_core.plan_stubs import prompt_user_for_choice
from ibex_bluesky_core.plans import scan

logger = logging.getLogger(__name__)


def _print_and_log(msg: str) -> None:
    logger.info(msg)
    print(msg)


def _check_parameter(
    alignment_param_value: float,
    result: ModelResult,
    init_mot_pos: float,
    rel_scan_range: float,
    is_good_fit: Callable[[ModelResult, float], str | None] | None = None,
) -> str | None:
    """Check that the optimised value is within scan range and then runs user provided checks.

    Returns True means the found result was sensible.

    Args:
        alignment_param_value (float): The name of the optimised value.
        result (ModelResult): The fitting result returned from lmfit.
        init_mot_pos (float): The initial motor position before scanning.
        rel_scan_range (float): The current relative scan range.
        is_good_fit (Callable[[ModelResult, float], str] | None): User provided checks on the
            optimised value, must return a message if result is not sensible.

    Returns:
        True if value is sensible. False otherwise.

    """
    upper = init_mot_pos + rel_scan_range / 2
    lower = init_mot_pos - rel_scan_range / 2

    logger.info("Checking fit parameter")
    if alignment_param_value > upper:
        return "Optimised value found to be to be outside, to the right, of scan range"

    elif alignment_param_value < lower:
        return "Optimised value found to be to be outside, to the left, of scan range"

    if is_good_fit is None:
        logger.info("No user-level is_good_fit function supplied and value in scan range")
        return None

    is_good = is_good_fit(result, alignment_param_value)
    logger.info("User-level is_good_fit function returned: %s", is_good)
    return is_good


def _optimise_axis_over_range(  # noqa: PLR0913 PLR0917
    dae: SimpleDae,
    alignment_param: NamedMovable[float],
    fit_param: str,
    rel_scan_range: float,
    num_points: int,
    fit_method: FitMethod,
    periods: bool,
    save_run: bool,
    is_good_fit: Callable[[ModelResult, float], str | None] | None,
    problem_found_plan: Callable[[], Generator[Msg, None, None]],
) -> Generator[Msg, None, tuple[ISISCallbacks, bool]]:
    """Functionality to perform on a per scan basis.

    Args:
        dae (SimpleDae): A readable DAE object.
        alignment_param (AlignmentParam): The alignment parameter to be scanned over and optimised.
        fit_param (str): Which property of fit_method you aim to optimise. e.g centre (x0)
            of a Gaussian. See :mod:`ibex_bluesky_core.fitting` for the
            possible options for each fitting method.
        rel_scan_range (float): The current relative scan range.
        num_points (int): The number of points across the scan.
        fit_method (FitMethod): The relationship to expect between the alignment parameter
            and the beam. e.g Gaussian.
        periods (bool): Are DAE periods being used. Defaults to True.
        save_run (bool): Should runs be saved. Defaults to True.
        is_good_fit (Callable[[ModelResult, float], str | None] | None): User provided checks on the
            optimised value, must return True if result is sensible.
        problem_found_plan (Callable[[], Generator[Msg, None, None]] | None]):
            A callback for what to do if the optimised value is not found to be sensible.

    Returns:
        Tuple of [ISISCallbacks, success (bool)]. The ISISCallbacks are a reference to a set of
        standard callbacks, including the fit.
        The success flag indicates whether the optimization was successful.

    """
    _print_and_log(
        f"Scanning over {alignment_param.name} with a relative scan range of {rel_scan_range}."
    )

    init_mot_pos: float = yield from bps.rd(alignment_param)  # type: ignore
    logger.info("initial position: %s", init_mot_pos)

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
    logger.info("scan finished.")

    try:
        alignment_param_value = icc.live_fit.result.values[fit_param]
    except (AttributeError, ValueError, KeyError):
        alignment_param_value = init_mot_pos
        problem = "fit failed to converge (fit value set to original position of motor)"
    else:
        problem = _check_parameter(
            alignment_param_value=alignment_param_value,
            result=icc.live_fit.result,
            init_mot_pos=init_mot_pos,
            rel_scan_range=rel_scan_range,
            is_good_fit=is_good_fit,
        )

    if problem is not None:
        logger.info("Problem encountered during fit: %s", problem)
        _print_and_log(
            f"This failed one or more of the checks on {alignment_param.name}"
            f" with a scan range of {rel_scan_range}. Problem was {problem}"
        )
        _print_and_log(f"Value found for {fit_param} was {alignment_param_value}.")

        yield from problem_found_plan()

        choice = yield from prompt_user_for_choice(
            prompt=f"Type '1' if you would like to re-scan or type '2' to "
            f"move {alignment_param.name} to {alignment_param_value} and keep going.",
            choices=["1", "2"],
        )
        if choice == "1":
            return icc, False

    _print_and_log(f"Moving {alignment_param.name} to {alignment_param_value}.")
    yield from bps.mv(alignment_param, alignment_param_value)

    return icc, True


def optimise_axis_against_intensity(  # noqa: PLR0913
    dae: SimpleDae,
    alignment_param: NamedMovable[float],
    fit_method: FitMethod,
    fit_param: str,
    rel_scan_ranges: list[float],
    *,
    num_points: int = 10,
    periods: bool = True,
    save_run: bool = True,
    problem_found_plan: Callable[[], Generator[Msg, None, None]] | None = None,
    is_good_fit: Callable[[ModelResult, float], str | None] | None = None,
) -> Generator[Msg, None, ISISCallbacks | None]:
    """Optimise a motor/device to the intensity of the beam.

    Scan between two symmetrical points relative to alignment_param's current motor position,
    to find where the optimal point is depending on fit_param, and move to it,
    then optionally repeat the process for a smaller range and higher granularity.

    Note:
        This plan does not redefine the position of the movable as zero - that should
        be done in caller plans

    Args:
        dae (SimpleDae): A readable signal that represents beam intensity.
        alignment_param (AlignmentParam): The alignment parameter to be scanned over and optimised.
        fit_method (FitMethod): The relationship to expect between the alignment parameter
            and the beam. e.g Gaussian.
        fit_param (str): Which property of fit_method you aim to optimise. e.g centre (x0)
            of a Gaussian. See :mod:`ibex_bluesky_core.fitting` for the possible options
            for each fitting method.
        rel_scan_ranges (list[float]): Scan range relative to the current motor position.
            If the list has more than one element then it will rescan for each range.
            Scans between mot_pos - rel_scan_range / 2 -> mot_pos + rel_scan_range / 2
        num_points (int): The number of points across the scan. Defaults to 10.
        periods (bool): Are DAE periods being used. Defaults to True.
        save_run (bool): Should runs be saved. Defaults to True.
        problem_found_plan (Callable[[], Generator[Msg, None, None]] | None):
            A plan, called if optimised value is not found to be
            sensible.
        is_good_fit (Callable[[ModelResult, float], bool] | None): User provided checks on the
            optimised value, must return True if result is sensible.

    Returns:
        Instance of :obj:`ibex_bluesky_core.callbacks.ISISCallbacks`.

    """
    problem_found_plan = problem_found_plan or bps.null

    logger.info(
        "Starting optimise_axis_against_intensity with param=%s, ranges=%s",
        alignment_param.name,
        rel_scan_ranges,
    )

    while True:  # If a problem is found, then start the alignment again
        all_ok = True
        icc = None

        for rel_scan_range in rel_scan_ranges:
            icc, all_ok = yield from _optimise_axis_over_range(
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

            if not all_ok:
                logger.info("Problem found during _optimise_axis_over_range, restarting scan loop")
                break

        if all_ok:
            logger.info(
                "Finished optimise_axis_against_intensity with param=%s, ranges=%s",
                alignment_param.name,
                rel_scan_ranges,
            )
            return icc
