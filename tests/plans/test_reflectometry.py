# pyright: reportMissingParameterType=false
import functools
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import bluesky.plan_stubs as bps
import pytest
from bluesky.utils import Msg
from lmfit.model import ModelResult

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.devices.reflectometry import ReflParameter
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.fitting import Gaussian, SlitScan
from ibex_bluesky_core.plans.reflectometry import (
    optimise_axis_against_intensity,
    refl_adaptive_scan,
    refl_scan,
)
from ibex_bluesky_core.plans.reflectometry._autoalign import (
    _check_parameter,
    _optimise_axis_over_range,
)


@pytest.fixture
def prefix():
    return "UNITTEST:"


def _plan_return_0() -> Generator[Msg, None, float]:
    yield from bps.null()
    return 0.0


def _fake_scan() -> Generator[Msg, None, ISISCallbacks]:
    yield from bps.null()
    icc = MagicMock()
    icc.live_fit.result = "foo"
    return icc


def test_refl_scan_creates_refl_param_device_and_simpledae(RE, prefix):
    param_name = "theta"
    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.devices.simpledae.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.plans.reflectometry.scan") as scan,
    ):
        RE(
            refl_scan(
                param=param_name,
                start=0,
                stop=2,
                num=3,
                frames=200,
                det=1,
                mon=3,
                model=Gaussian().fit(),
            )
        )
        scan.assert_called_once()
        assert isinstance(scan.call_args[1]["dae"], SimpleDae)
        assert isinstance(scan.call_args[1]["block"], ReflParameter)
        assert scan.call_args[1]["block"].name == param_name


def test_refl_adaptive_scan_creates_refl_param_device_and_simpledae(RE, prefix):
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
                det=1,
                mon=3,
                model=Gaussian().fit(),
            )
        )
        scan.assert_called_once()
        assert isinstance(scan.call_args[1]["dae"], SimpleDae)
        assert isinstance(scan.call_args[1]["block"], ReflParameter)
        assert scan.call_args[1]["block"].name == param_name


# Auto-Alignment Utils


def test_found_problem_callback_is_called_if_problem(RE, simpledae, prefix, monkeypatch):
    """Test that if a problem is found then the problem callback plan is run"""

    def plan(mock) -> Generator[Msg, None, None]:
        mock()
        yield from bps.null()
        return None

    mock = MagicMock()

    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.plans.reflectometry._autoalign.scan", return_value=_fake_scan()),
        patch("ibex_bluesky_core.plans.reflectometry._autoalign.bps.mv", return_value=bps.null()),
        patch(
            "ibex_bluesky_core.plans.reflectometry._autoalign.bps.rd",
            return_value=_plan_return_0(),
        ),
        patch(
            "ibex_bluesky_core.plans.reflectometry._autoalign._check_parameter",
            side_effect=["Test!", None],
        ),
    ):
        param = ReflParameter(prefix=prefix, name="S1VG", changing_timeout_s=60)

        monkeypatch.setattr("builtins.input", lambda _: "2")
        RE(
            optimise_axis_against_intensity(
                dae=simpledae,
                alignment_param=param,
                problem_found_plan=functools.partial(plan, mock),
                rel_scan_ranges=[0.0],
                fit_method=SlitScan().fit(),
                fit_param="",
            )
        )

        mock.assert_called_once()


@pytest.mark.parametrize(
    ("param_value", "problem_str"),
    [
        (-5, "Optimised value found to be to be outside, to the left, of scan range"),
        (5, "Optimised value found to be to be outside, to the right, of scan range"),
        (0, None),
    ],
)
def test_alignment_param_value_outside_of_scan_range_returns_problem(param_value, problem_str):
    """Test that if the optimised value is outside of the scan range then it is reported"""
    with (
        patch("lmfit.model.ModelResult") as mr,
    ):
        assert (
            _check_parameter(
                alignment_param_value=param_value,
                result=mr,
                init_mot_pos=0.0,
                rel_scan_range=1.0,
            )
            == problem_str
        )


@pytest.mark.parametrize("problem", [False, True])
def test_that_user_checks_are_called_when_provided(problem):
    """Test that a user provided check function on the optimised value is always ran"""
    mock = MagicMock()

    def my_check(model: ModelResult, param_val: float) -> str | None:
        mock()

        if problem:
            return "problem"

    with patch("lmfit.model.ModelResult") as mr:
        mr.values = {"x0": 0.0}

        assert ("problem" if problem else None) == _check_parameter(
            alignment_param_value=0.0,
            result=mr,
            init_mot_pos=0.0,
            rel_scan_range=1.0,
            is_good_fit=my_check,
        )


def test_that_if_no_problem_found_then_motor_is_moved(RE, prefix, simpledae):
    """Test that if no problems are found with the optimised
    value then move the motor to it
    """

    icc = MagicMock(spec=ISISCallbacks)
    icc.live_fit.fit_result.params[""] = 0.0

    def mock_scan(*a, **k):
        yield from bps.null()
        return icc

    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch(
            "ibex_bluesky_core.plans.reflectometry._autoalign._check_parameter",
            return_value=None,
        ) as check,
        patch("ibex_bluesky_core.plans.reflectometry._autoalign.scan", return_value=_fake_scan()),
        patch(
            "ibex_bluesky_core.plans.reflectometry._autoalign.bps.mv", return_value=bps.null()
        ) as mv,
        patch(
            "ibex_bluesky_core.plans.reflectometry._autoalign.bps.rd",
            return_value=_plan_return_0(),
        ),
        patch(
            "ibex_bluesky_core.plans.reflectometry._autoalign.scan",
            new=mock_scan,
        ),
    ):
        param = ReflParameter(prefix=prefix, name="S1VG", changing_timeout_s=60)

        RE(
            _optimise_axis_over_range(
                simpledae,
                alignment_param=param,
                rel_scan_range=0.0,
                fit_method=SlitScan().fit(),
                fit_param="",
                num_points=10,
                periods=True,
                save_run=True,
                is_good_fit=lambda *a, **k: None,
                problem_found_plan=bps.null,
            )
        )

        check.assert_called_once()
        mv.assert_called_once()


def test_that_if_problem_found_and_type_1_then_re_scan(RE, prefix, simpledae, monkeypatch):
    """Test that if a problem is found, and the user types 1, then rescan.
    Then if they type 2, moves to value.
    """
    call_count = 0

    def counter(str: str):
        nonlocal call_count
        call_count += 1  # type: ignore

        if call_count == 1:  # type: ignore
            return "1"
        else:
            return "2"

    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch(
            "ibex_bluesky_core.plans.reflectometry._autoalign._check_parameter",
            return_value="Test!",
        ),
        patch(
            "ibex_bluesky_core.plans.reflectometry._autoalign.scan",
            side_effect=[_fake_scan(), _fake_scan()],
        ) as scan,
        patch("ibex_bluesky_core.plans.reflectometry._autoalign.bps.mv", return_value=bps.null()),
        patch(
            "ibex_bluesky_core.plans.reflectometry._autoalign.bps.rd",
            return_value=_plan_return_0(),
        ),
    ):
        param = ReflParameter(prefix=prefix, name="S1VG", changing_timeout_s=60)

        monkeypatch.setattr("builtins.input", counter)
        RE(
            optimise_axis_against_intensity(
                simpledae,
                alignment_param=param,
                rel_scan_ranges=[0.0],
                fit_method=SlitScan().fit(),
                fit_param="",
            )
        )

        assert scan.call_count == 2


def test_that_if_problem_found_and_type_random_then_re_ask(RE, prefix, simpledae, monkeypatch):
    """Test that if a problem is found, and the user types gibberish, then ask again.
    Then if they type 1, it rescans. If they type 2, it moves to value.
    """
    call_count = 0

    def counter(str: str):
        nonlocal call_count
        call_count += 1

        if call_count == 1:  # type: ignore
            return "platypus"
        elif call_count == 2:  # type: ignore
            return "1"
        else:
            return "2"

    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch(
            "ibex_bluesky_core.plans.reflectometry._autoalign._check_parameter",
            return_value="Test!",
        ),
        patch(
            "ibex_bluesky_core.plans.reflectometry._autoalign.scan",
            side_effect=[_fake_scan(), _fake_scan()],
        ) as scan,
        patch("ibex_bluesky_core.plans.reflectometry._autoalign.bps.mv", return_value=bps.null()),
        patch(
            "ibex_bluesky_core.plans.reflectometry._autoalign.bps.rd",
            return_value=_plan_return_0(),
        ),
    ):
        param = ReflParameter(prefix=prefix, name="S1VG", changing_timeout_s=60)

        monkeypatch.setattr("builtins.input", counter)
        RE(
            optimise_axis_against_intensity(
                simpledae,
                alignment_param=param,
                rel_scan_ranges=[10.0],
                fit_method=SlitScan().fit(),
                fit_param="",
            )
        )

        assert scan.call_count == 2
