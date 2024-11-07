# Why do we add 0.5 to variance?

## Status

Current

## Context

If we pass counts data to `scipp` as variance this is correct- but if one of the counts is 0 then its variance is 0, leading to a division by 0 error when calculating its weight for fitting `weight = 1 / doc["data"][self.yerr]`. See `src\ibex_bluesky_core\devices\dae\dae_spectra.py line 118`.

## Decision

Our solution was to add 0.5 (`VARIANCE_ADDITION`) to each count to calculate variance. The actual data should be unchanged, the +0.5 is only for uncertainty calculation.

## Justification

The above approach is both "smooth" and converges towards sqrt(N) in the limit with high counts, and should also mean that we never get an uncertainty of zero in the fitting side.