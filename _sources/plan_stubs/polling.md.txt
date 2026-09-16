# Continuous polling

{py:obj}`ibex_bluesky_core.plans.polling_plan` can be used to perform a software continuous scan - setting off a motor
move, and then monitoring both the motor position and a readable, zipping them together into a single dataset suitable
for our usual plotting and fitting callbacks.

Updates from the readable may be dropped if they occur at a higher rate than updates from the motor position.

{py:obj}`~ibex_bluesky_core.plans.polling_plan` does not start a bluesky run, so you will need to use a {py:obj}`~bluesky.preprocessors.run_decorator` on an outer plan which calls this plan stub. This is so that _multiple_ continuous moves can be done as part of the same bluesky run.
