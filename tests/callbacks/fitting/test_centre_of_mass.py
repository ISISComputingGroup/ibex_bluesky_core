import pytest

from ibex_bluesky_core.callbacks.fitting import PeakStats


@pytest.mark.parametrize(
    ("data", "expected_com"),
    [
        # Simplest case:
        # - Flat, non-zero Y data
        # - Evenly spaced, monotonically increasing X data
        ([(0, 1), (2, 1), (4, 1), (6, 1), (8, 1), (10, 1)], 5.0),
        # Simple triangular peak
        ([(0, 0), (1, 1), (2, 2), (3, 1), (4, 0), (5, 0)], 2.0),
        # Simple triangular peak with non-zero base
        ([(0, 10), (1, 11), (2, 12), (3, 11), (4, 10), (5, 10)], 2.0),
        # No data at all
        ([], None),
        # Only one point, com should be at that one point regardless whether it
        # measured zero or some other y value.
        ([(5, 0)], 5.0),
        ([(5, 50)], 5.0),
        # Two points, flat data, com should be in the middle
        ([(0, 5), (10, 5)], 5.0),
        # Flat, logarithmically spaced data - CoM should be in centre of measured range.
        ([(1, 3), (10, 3), (100, 3), (1000, 3), (10000, 3)], 5000.5),
        # "triangle" defined by area under two points
        # (CoM of a right triangle is 1/3 along x from right angle)
        ([(0, 0), (3, 6)], 2.0),
        ([(0, 6), (3, 0)], 1.0),
        # Cases with the first/last points not having equal spacings with each other
        ([(0, 1), (0.1, 1), (4, 1), (5, 0), (6, 1), (10, 1)], 5.0),
        ([(0, 1), (4, 1), (5, 0), (6, 1), (9.9, 1), (10, 1)], 5.0),
        # Two triangular peaks next to each other, with different point spacings
        # but same shapes, over a base of zero.
        ([(0, 0), (1, 1), (2, 2), (3, 1), (4, 0), (6, 2), (8, 0), (10, 0)], 4.0),
        ([(0, 0), (2, 2), (4, 0), (5, 1), (6, 2), (7, 1), (8, 0), (10, 0)], 4.0),
        # Two triangular peaks next to each other, with different point spacings
        # but same shapes, over a base of 10.
        ([(0, 10), (1, 11), (2, 12), (3, 11), (4, 10), (6, 12), (8, 10), (10, 10)], 4.0),
        ([(0, 10), (2, 12), (4, 10), (5, 11), (6, 12), (7, 11), (8, 10), (10, 10)], 4.0),
        # "Narrow" peak over a base of 0
        ([(0, 0), (4.999, 0), (5.0, 10), (5.001, 0)], 5.0),
        # "Narrow" peak as above, over a base of 10 (y translation should not
        # affect CoM)
        ([(0, 10), (4.999, 10), (5.0, 20), (5.001, 10)], 5.0),
        # Non-monotonically increasing x data (e.g. from adaptive scan)
        ([(0, 0), (2, 2), (1, 1), (3, 1), (4, 0)], 2.0),
        # Overscanned data (all measurements duplicated, e.g. there-and-back scan)
        ([(0, 0), (1, 1), (2, 0), (2, 0), (1, 1), (0, 0)], 1.0),
        # Mixed positive/negative data. This explicitly calculates area *under* curve,
        # so CoM should still be the CoM of the positive peak in this data.
        ([(0, -1), (1, 0), (2, -1), (3, -1)], 1.0),
        # Y data with a single positive peak, which happens
        # to sum to zero but never contains zero.
        ([(0, -1), (1, 3), (2, -1), (3, -1)], 1.0),
        # Y data which happens to sum to *nearly* zero
        ([(0, -1), (1, 3.000001), (2, -1), (3, -1)], 1.0),
    ],
)
def test_compute_com(data: list[tuple[float, float]], expected_com):
    ps = PeakStats("x", "y")
    ps.start({})  # pyright: ignore

    for x, y in data:
        ps.event({"data": {"x": x, "y": y}})  # pyright: ignore

    ps.stop({})  # pyright: ignore
    assert ps["com"] == pytest.approx(expected_com)
