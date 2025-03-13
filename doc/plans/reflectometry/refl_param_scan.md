# Reflectometry parameter scan

{py:obj}`ibex_bluesky_core.plans.reflectometry.refl_scan`
{py:obj}`ibex_bluesky_core.plans.reflectometry.refl_adaptive_scan`

These are very similar to the general high-level plans, but are designed to construct a DAE and a {py:obj}`ReflParameter<ibex_bluesky_core.devices.reflectometry.ReflParameter>` given a reflectometry server parameter name (ie. "S1VG" or "THETA"). The reflectometry server has some logic which tell us if sets and redefines were successful, so we provide devices that utilise this. 
