"""Top-level ``ibex_bluesky_core`` library.

The ``ibex_bluesky_core`` library Integrates the
:external+ibex_user_manual:doc:`IBEX control system <index>` and the
:external+bluesky:doc:`bluesky data acquisition library <index>`, by
providing:

- ISIS-specific bluesky devices
- Common callbacks, plans, and plan stubs for ISIS beamlines
- ISIS-specific :py:obj:`~bluesky.run_engine.RunEngine` configuration

See Also:
    - :doc:`User documentation </index>`.
    - :doc:`/tutorial/overview` for an introduction to concepts in ``ibex_bluesky_core``.

"""

from ibex_bluesky_core.log import setup_logging

__all__ = []

setup_logging()
