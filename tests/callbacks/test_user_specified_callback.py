import typing

import bluesky.plans as bp
import bluesky.preprocessors as bpp
import numpy as np
import numpy.typing as npt
import pytest
from bluesky import RunEngine
from bluesky.run_engine import RunEngineResult
from ophyd_async.core import soft_signal_rw

from ibex_bluesky_core.callbacks import CustomCallback


def test_user_specified_callback_with_y_err(RE: RunEngine):
    x = soft_signal_rw(float, 3, "my_x")
    y = soft_signal_rw(float, 4, "my_y")
    y_err = soft_signal_rw(float, 5, "my_y_err")

    def callback(
        x: npt.NDArray[np.float64],
        y: npt.NDArray[np.float64],
        y_err: npt.NDArray[np.float64] | None,
    ) -> tuple[float, float, float, float]:
        if y_err is None:
            raise ValueError("y_err cannot be None")
        return x.mean(), y.mean(), y_err.mean(), 42

    def plan():
        custom_callback = CustomCallback(
            func=callback,
            x="my_x",
            y="my_y",
            y_err="my_y_err",
        )

        @bpp.subs_decorator([custom_callback])
        def _inner():
            yield from bp.count([x, y, y_err])

        yield from _inner()
        result = custom_callback.result
        assert result is not None
        average_x, average_y, average_y_err, the_answer = result
        return average_x, average_y, average_y_err, the_answer

    result: RunEngineResult = typing.cast(RunEngineResult, RE(plan()))

    assert result.plan_result[0] == pytest.approx(3)
    assert result.plan_result[1] == pytest.approx(4)
    assert result.plan_result[2] == pytest.approx(5)
    assert result.plan_result[3] == pytest.approx(42)


def test_user_specified_callback_without_y_err(RE: RunEngine):
    x = soft_signal_rw(float, 3, "my_x")
    y = soft_signal_rw(float, 4, "my_y")

    def callback(
        x: npt.NDArray[np.float64],
        y: npt.NDArray[np.float64],
        y_err: npt.NDArray[np.float64] | None,
    ) -> tuple[float, float, float]:
        return x.mean(), y.mean(), 73

    def plan():
        custom_callback = CustomCallback(
            func=callback,
            x="my_x",
            y="my_y",
        )

        @bpp.subs_decorator([custom_callback])
        def _inner():
            yield from bp.count([x, y])

        yield from _inner()
        result = custom_callback.result
        assert result is not None
        average_x, average_y, the_answer = result
        return average_x, average_y, the_answer

    result: RunEngineResult = typing.cast(RunEngineResult, RE(plan()))

    assert result.plan_result[0] == pytest.approx(3)
    assert result.plan_result[1] == pytest.approx(4)
    assert result.plan_result[2] == pytest.approx(73)
