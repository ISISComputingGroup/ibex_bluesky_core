# Continuous polling

[`polling_plan`](ibex_bluesky_core.plans.polling_plan) - is used for moving a motor and dropping updates from a "readable" if no motor updates are provided. An example of this is a laser reading which updates much more quickly than a motor might register it's moved, so the laser readings are not really useful information.

This in itself doesn't start a bluesky "run" so you will need to use a `run_decorator` on any outer plan which calls this plan stub. 

