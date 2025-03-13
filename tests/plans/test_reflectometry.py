# pyright: reportMissingParameterType=false

from typing import Generator, Iterator
from unittest.mock import MagicMock, Mock, patch

import pytest

from ibex_bluesky_core.callbacks.fitting import LiveFit
from ibex_bluesky_core.devices.block import BlockMot, BlockRw
from ibex_bluesky_core.devices.reflectometry import ReflParameter
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import RunPerPointController
from ibex_bluesky_core.devices.simpledae.reducers import MonitorNormalizer
from ibex_bluesky_core.devices.simpledae.strategies import Waiter
from ibex_bluesky_core.plans.reflectometry import refl_adaptive_scan, refl_scan
from ibex_bluesky_core.plans.reflectometry import autoalign_utils
from ibex_bluesky_core.plans.reflectometry.autoalign_utils import AlignmentParam, _add_fields, optimise_axis_against_intensity
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Fit, SlitScan
import bluesky.plan_stubs as bps 
from bluesky.utils import Msg


def test_refl_scan_creates_refl_param_device_and_dae(RE):
    prefix = "UNITTEST:"
    param_name = "theta"
    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.devices.simpledae.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.plans.reflectometry.scan") as scan,
    ):
        RE(refl_scan(param=param_name, start=0, stop=2, count=3, frames=200))
        scan.assert_called_once()
        assert isinstance(scan.call_args[1]["dae"], SimpleDae)
        assert isinstance(scan.call_args[1]["block"], ReflParameter)
        assert scan.call_args[1]["block"].name == param_name


def test_refl_adaptive_scan_creates_refl_param_device_and_dae(RE):
    prefix = "UNITTEST:"
    param_name = "S1VG"
    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.devices.simpledae.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.plans.reflectometry.adaptive_scan") as scan,
    ):
        RE(
            refl_adaptive_scan(
                param=param_name,
                start=0,
                stop=2,
                min_step=0.01,
                max_step=0.1,
                target_delta=0.5,
                frames=200,
            )
        )
        scan.assert_called_once()
        assert isinstance(scan.call_args[1]["dae"], SimpleDae)
        assert isinstance(scan.call_args[1]["block"], ReflParameter)
        assert scan.call_args[1]["block"].name == param_name

##################### autoalign_utils


@pytest.fixture
async def dae():
    controller = RunPerPointController(save_run=True)
    noop_waiter = Waiter()
    reducer = MonitorNormalizer(prefix="UNITTEST:", detector_spectra=[1, 2, 3], monitor_spectra=[4])

    dae = SimpleDae(
        prefix="UNITTEST:",
        name="dae",
        controller=controller,
        waiter=noop_waiter,
        reducer=reducer,
    )
    await dae.connect(mock=True)
    return dae

def test_get_movable_on_alignment_param_returns_reflparam():

    param = AlignmentParam(name="S1VG", rel_scan_ranges=[0.0], fit_method=Fit.fit(), fit_param="")

    assert type(param.get_movable()) is ReflParameter
    assert param.get_movable().name == param.name


def test_alignment_param_pre_alignment_plan(RE):

    params = [

        AlignmentParam(name="S1VG", rel_scan_ranges=[0.0], fit_method=Fit.fit(), fit_param="", pre_align_param_positions={"S1VG": 1.0, "S2VG": 2.0, "S3VG": 3.0}),
        AlignmentParam(name="S2VG", rel_scan_ranges=[0.0], fit_method=Fit.fit(), fit_param=""),
        AlignmentParam(name="S3VG", rel_scan_ranges=[5.0, 1.0, 0.1], fit_method=Fit.fit(), fit_param="")

    ]

    prefix = "UNITTEST:"
    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch("bluesky.plan_stubs.mv") as mv
    ):
        RE(params[0].pre_align_params(params))

        mv.assert_called_once()
        assert mv.call_args[0] == (params[0].get_movable(), 1.0, params[1].get_movable(), 2.0, params[2].get_movable(), 3.0)


def test_when_no_fields_provided_then_fields_added(RE, dae):

    param = AlignmentParam(name="S1VG", rel_scan_ranges=[], fit_method=SlitScan().fit(), fit_param="")

    def gen() -> Generator[Msg, None, float]:
        yield from bps.null()
        return 0.0

    with (
        patch("ibex_bluesky_core.plans.ISISCallbacks.__init__", return_value=None) as icc,
        patch("ibex_bluesky_core.plans.ISISCallbacks.live_fit", return_value=LiveFit(param.fit_method, dae.name, param.name)),
        patch("bluesky.plan_stubs.rd", return_value=gen())
    ):
        
        RE(optimise_axis_against_intensity(dae, alignment_param=param))
        
        icc.assert_called_once()
        assert [dae.reducer.intensity.name, dae.reducer.intensity_stddev.name, dae.period_num.name, dae.controller.run_number.name, "S1VG"] == icc.call_args[1]["measured_fields"] # type: ignore


def test_pre_post_align_callbacks_are_called(RE, dae):

    def plan(mock) -> Generator[Msg, None, None]:
        mock()
        yield from bps.null()

    def gen() -> Generator[Msg, None, bool]:
        yield from bps.null()
        return True

    mock_a = MagicMock()
    mock_b = MagicMock()

    param = AlignmentParam(name="S1VG", rel_scan_ranges=[], fit_method=SlitScan().fit(), fit_param="")

    with (
        patch("ibex_bluesky_core.plans.reflectometry.autoalign_utils._inner_loop", return_value=gen())
    ):
        
        RE(optimise_axis_against_intensity(dae, alignment_param=param, pre_align_plan=lambda: plan(mock_a), post_align_plan=lambda: plan(mock_b)))
        
        mock_a.assert_called_once()
        mock_b.assert_called_once()


def test_found_problem_callback_is_called_if_problem(RE, dae, monkeypatch):

    def plan(mock) -> Generator[Msg, None, None]:
        mock()
        yield from bps.null()

    def gen() -> Generator[Msg, None, float]:
        yield from bps.null()
        return 0.0

    mock = MagicMock()
    param = AlignmentParam(name="S1VG", rel_scan_ranges=[0.0], fit_method=SlitScan().fit(), fit_param="")

    with (
        patch("bluesky.plans.rel_scan", return_value=bps.null()),
        patch("bluesky.plan_stubs.mv", return_value=bps.null()),
        patch("bluesky.plan_stubs.rd", return_value=gen())
    ):
        monkeypatch.setattr('builtins.input', lambda _: '2')
        RE(optimise_axis_against_intensity(dae, alignment_param=param, problem_found_plan=lambda: plan(mock)))
        mock.assert_called_once()
