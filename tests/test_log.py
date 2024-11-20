import logging
from unittest.mock import patch

import pytest

from ibex_bluesky_core.log import file_handler, set_bluesky_log_levels, setup_logging


@pytest.mark.parametrize("name", ["ibex_bluesky_core", "ophyd_async", "bluesky"])
def test_setup_logging(name: str):
    logging.getLogger(name).handlers.clear()
    setup_logging()
    assert any(handler == file_handler() for handler in logging.getLogger(name).handlers)


def test_setup_logging_does_not_add_handler_to_root_logger():
    setup_logging()
    assert not any(handler == file_handler() for handler in logging.getLogger().handlers)


def test_setup_logging_does_not_crash_if_directory_cannot_be_created(
    capfd: pytest.CaptureFixture[str],
):
    with patch("ibex_bluesky_core.log.os.makedirs") as mock_makedirs:
        mock_makedirs.side_effect = OSError
        setup_logging()

    stdout, stderr = capfd.readouterr()
    assert stderr == "unable to create ibex_bluesky_core log directory\n"


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR"])
def test_set_bluesky_log_levels_explicit(level: str):
    set_bluesky_log_levels(level)
    for name in ["ibex_bluesky_core", "ophyd_async", "bluesky"]:
        assert logging.getLevelName(logging.getLogger(name).level) == level


def test_set_bluesky_log_levels_default_previously_unset():
    # Setup, pretend log levels have never been set
    set_bluesky_log_levels(logging.NOTSET)

    # If the levels weren't previously set, override them to INFO
    set_bluesky_log_levels()

    for name in ["ibex_bluesky_core", "ophyd_async", "bluesky"]:
        assert logging.getLogger(name).level == logging.INFO


def test_set_bluesky_log_levels_default_previously_set():
    # Setup, set some explicit log levels on various loggers.
    logging.getLogger("ibex_bluesky_core").setLevel(logging.WARN)
    logging.getLogger("bluesky").setLevel(logging.INFO)
    logging.getLogger("ophyd_async").setLevel(logging.DEBUG)

    set_bluesky_log_levels()

    # Assert we didn't override the previously explicitly-set levels
    assert logging.getLogger("ibex_bluesky_core").level == logging.WARN
    assert logging.getLogger("bluesky").level == logging.INFO
    assert logging.getLogger("ophyd_async").level == logging.DEBUG
