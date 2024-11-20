# Variance addition to counts data

## Status

Current

## Context

For counts data, the uncertainty on counts is typically defined by poisson counting statistics, i.e. the standard deviation on `N` counts is `sqrt(N)`.

This can be problematic in cases where zero counts have been collected, as the standard deviation will then be zero, which will subsequently lead to "infinite" point weightings in downstream fitting routines for example.

A number of possible approaches were considered:

| Option | Description |
| --- | --- |
| A | Reject data with zero counts, i.e. explicitly throw an exception if any data with zero counts is seen as part of a scan. |
| B | Use a standard deviation of `NaN` for points with zero counts. |
| C | Define the standard deviation of `N` counts as `1` if counts are zero, otherwise `sqrt(N)`. This is one of the approaches available in mantid for example. |
| D | Define the standard deviation of `N` counts as `sqrt(N+0.5)` unconditionally - on the basis that "half a count" is smaller than the smallest possible actual measurement which can be taken. |
| E | No special handling, calculate std. dev. as `sqrt(N)`. |

For clarity, the following table shows the value and associated uncertainty for each option:

| Counts | Std. Dev. (A) | Std. Dev. (B) | Std. Dev. (C) | Std. Dev. (D) | Std. Dev. (E) |
| ------- | ------ | ------- | ------- | ------- | --- |
| 0 | raise exception | NaN | 1 | 0.707 | 0 |
| 1 | 1 | 1 | 1 | 1.224745 | 1 |
| 2 | 1.414214 | 1.414214 | 1.414214 | 1.581139 | 1.414214 |
| 3 | 1.732051 | 1.732051 | 1.732051 | 1.870829 | 1.732051 |
| 4 | 2 | 2 | 2 | 2.12132 | 2 |
| 5 | 2.236068 | 2.236068 | 2.236068 | 2.345208 | 2.236068 |
| 10 | 3.162278 | 3.162278 | 3.162278 | 3.24037 | 3.162278 |
| 50 | 7.071068 | 7.071068 | 7.071068 | 7.106335 | 7.071068 |
| 100 | 10 | 10 | 10 | 10.02497 | 10 |
| 500 | 22.36068 | 22.36068 | 22.36068 | 22.37186 | 22.36068 |
| 1000 | 31.62278 | 31.62278 | 31.62278 | 31.63068 | 31.62278 |
| 5000 | 70.71068 | 70.71068 | 70.71068 | 70.71421 | 70.71068 |
| 10000 | 100 | 100 | 100 | 100.0025 | 100 |

## Present

These approaches were discussed in a regular project update meeting including
- TW & FA (Experiment controls)
- CK (Reflectometry)
- JL (Muons)
- RD (SANS)

## Decision

The consensus was to go with Option D.

## Justification

- Option A will cause real-life scans to crash in low counts regions.
- Option B involves `NaN`s, which have many surprising floating-point characteristics and are highly likely to be a source of future bugs.
- Option D was preferred to option C by scientists present.
- Option E causes surprising results and/or crashes downstream, for example fitting may consider points with zero uncertainty to have "infinite" weight, therefore effectively disregarding all other data.
