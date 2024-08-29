from ibex_bluesky_core.utils.dehex_and_decompress import dehex_and_decompress


def test_can_dehex_and_decompress():
    expected = b"test123"
    hexed_and_compressed = b"789c2b492d2e31343206000aca0257"
    result = dehex_and_decompress(hexed_and_compressed)
    assert result == expected
