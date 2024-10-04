"""Demonstration plan showing basic bluesky functionality."""

import os
from typing import Generator

import bluesky.plan_stubs as bps
from bluesky.utils import Msg


def interruption_manual_test_plan() -> Generator[Msg, None, None]:
    """Manual system test that checks ctrl-c interruption of a plan.

    This test can only be usefully run from an interactive session.

    Expected result:
    - After ctrl-c twice:
      * A bluesky.utils.RunEngineInterrupted error should be raised
      * Useful text describing options (RE.halt(), RE.abort(), RE.resume()) should be printed
    - After RE.abort():
      * A RunEngineResult should be returned, with exit_status="abort"
      * A bluesky.utils.RequestAbort error should be raised
    """
    print("About to sleep - press ctrl-C twice to interrupt, then use RE.abort() to abort.")
    yield from bps.sleep(999999999)


if __name__ == "__main__" and not os.environ.get("FROM_IBEX") == "True":
    print("This system test should only be run from an interactive session.")
