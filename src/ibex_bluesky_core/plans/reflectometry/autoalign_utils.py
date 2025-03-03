from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Callable, NotRequired, TypedDict, Unpack
import bluesky.plans as bp
import bluesky.plan_stubs as bps
from bluesky.utils import Msg
from collections.abc import Generator
from lmfit.model import ModelResult
from ibex_bluesky_core.callbacks import ISISCallbacks as ICC
from ibex_bluesky_core.callbacks.fitting import FitMethod
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import BlockR, BlockRw
from ibex_bluesky_core.devices.reflectometry.refl_param import ReflParameter
from ibex_bluesky_core.devices.simpledae import SimpleDae
from datetime import datetime
from matplotlib.axes import Axes

FILE_OUTPUT_DIR = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"


@dataclass
class AlignmentParam:
        
    name: str
    rel_scan_range: float
    fit_method: FitMethod
    fit_param: str
    initial_pos: float = 0.0
    do_checks: Callable[[ModelResult, float], bool] | None = None
    _prefix: str = get_pv_prefix()
    _device: ReflParameter | BlockRw[float] | None = None

    def get_device(self):
        if not self._device:
            self._device = ReflParameter(prefix=self._prefix, name=self.name)
        return self._device
    
    def get_tuple(self):
        return (self.get_device(), self.initial_pos)


def pre_align(
    axes_list: list[AlignmentParam],
) -> Generator[Msg, None, None]:
    
    yield from bps.mv(*chain(*[(p.get_device(), p.initial_pos) for p in axes_list])) # type: ignore


def _add_fields(
    fields: list[str],
    dae: SimpleDae | BlockR[float],
    periods: bool,
    save_run: bool,
    device_name: str,
) -> list[str]:
    if fields is []:
        if type(dae) is SimpleDae:
            fields.append(
                [
                    dae.reducer.intensity.name,  # type: ignore
                    dae.reducer.intensity_stddev.name,  # type: ignore
                ]
            )

            if periods:
                fields.append(dae.period_num.name)  # type: ignore
            elif save_run:
                fields.append(dae.controller.run_number.name)  # type: ignore

        else:
            fields.append(dae.name)

        fields.append(device_name)

    return fields


def _check_parameter(
    param: float,
    result: ModelResult,
    init_mot_pos: float,
    rel_scan_range: float,
    user_checks: Callable[[ModelResult, float], bool] | None
) -> bool:

    #Check that found param is within scan range

    if init_mot_pos + rel_scan_range < param:
        return False

    elif init_mot_pos - rel_scan_range > param:
        return False

    if user_checks is None: return True
    return user_checks(result, param)
        
class OptimiseAxisParams(TypedDict):

    num_points: NotRequired[int]
    fields: NotRequired[list[str]]
    periods: NotRequired[bool]
    save_run: NotRequired[bool]
    files_output_dir: NotRequired[Path]
    user_checks: NotRequired[Callable[[ModelResult, float], bool] | None]
    callback_if_problem: NotRequired[Callable[[], None]]
    ax: NotRequired[Axes | None]

def optimise_axis_against_intensity(
    dae: SimpleDae | BlockR[float],
    device: ReflParameter | BlockRw[float],
    fit: FitMethod,
    optimised_param: str,
    rel_scan_range: float,
    **kwargs: Unpack[OptimiseAxisParams]
) -> Generator[Msg, None, ModelResult | None]:
    
    num_points = kwargs.get('num_points', 10)
    fields = kwargs.get('fields', [])
    periods = kwargs.get('periods', True)
    save_run = kwargs.get('save_run', True)
    files_output_dir = kwargs.get('files_output_dir', FILE_OUTPUT_DIR)
    user_checks = kwargs.get('user_checks', None)
    callback_if_problem = kwargs.get('callback_if_problem', lambda: None)
    ax = kwargs.get("ax", None)

    fields = _add_fields(
        fields, dae=dae, periods=periods, save_run=save_run, device_name=device.name
    )
    postfix = f"{device.name}_{datetime.now().strftime('%H%M%S')}"
    yerr = dae.reducer.intensity_stddev.name if type(dae) is SimpleDae else None # type: ignore

    icc = ICC(
        x=device.name,
        y=dae.name,
        yerr=yerr,
        measured_fields=fields,
        live_fit_logger_output_dir=files_output_dir,
        human_readable_file_output_dir=files_output_dir,
        fields_for_hr_file=fields,
        fit=fit,
        live_fit_logger_postfix=postfix,
        ax=ax,
    )

    init_mot_pos: float = yield from bps.rd(device)

    @icc
    def _inner() -> Generator[Msg, None, None]:
        yield from bp.rel_scan([dae], device, -rel_scan_range, rel_scan_range, num=num_points)

    yield from _inner()

    if icc.live_fit.result is None:
        return None

    print(icc.live_fit.result.fit_report())
    print(f"Files written to {FILE_OUTPUT_DIR}\n")
    param = icc.live_fit.result.values[optimised_param]

    sanity_check = _check_parameter(param=param,result=icc.live_fit.result, init_mot_pos=init_mot_pos,rel_scan_range=rel_scan_range,user_checks=user_checks)

    if not sanity_check:
        callback_if_problem()

        print(f"This failed one or more of the checks on {device.name}.")
        input("Check your setup and checking function then press enter to go again...")

        yield from optimise_axis_against_intensity(
            dae=dae,
            device=device,
            fit=fit,
            rel_scan_range=rel_scan_range,
            optimised_param=optimised_param,
            fields=fields,
            periods=periods,
            save_run=save_run,
            files_output_dir=files_output_dir,
        )

    else:
        print(f"Moving {device.name} to {param} and rezeroing...")
        yield from bps.mv(device, param)  # type: ignore
        # redefine motor pos to be 0 TODODDDDDDDDDDDDDDODODODOD!!!!!!!!!!!!!!!!!!!!!!!!!
    
    return icc.live_fit.result
