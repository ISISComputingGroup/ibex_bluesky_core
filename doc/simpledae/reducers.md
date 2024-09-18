# Reducers

A `Reducer` for a `SimpleDae` is responsible for publishing any data derived from the raw
DAE signals. For example, normalizing intensities are implemented as a reducer.

A reducer may produce any number of reduced signals.

## GoodFramesNormalizer

This normalizer sums a set of user-defined detector spectra, and then divides by the number
of good frames.

Published signals:
- `simpledae.good_frames` - the number of good frames reported by the DAE
- `reducer.det_counts` - summed detector counts for all of the user-provided spectra
- `reducer.intensity` - normalized intensity (`det_counts / good_frames`)

## PeriodGoodFramesNormalizer

Equivalent to the `GoodFramesNormalizer` above, but uses good frames only from the current
period. This should be used if a controller which counts into multiple periods is being used.

Published signals:
- `simpledae.period.good_frames` - the number of good frames reported by the DAE
- `reducer.det_counts` - summed detector counts for all of the user-provided spectra
- `reducer.intensity` - normalized intensity (`det_counts / good_frames`)

## DetectorMonitorNormalizer

This normalizer sums a set of user-defined detector spectra, and then divides by the sum
of a set of user-defined monitor spectra.

Published signals:
- `reducer.det_counts` - summed detector counts for the user-provided detector spectra
- `reducer.mon_counts` - summed monitor counts for the user-provided monitor spectra
- `reducer.intensity` - normalized intensity (`det_counts / mon_counts`)
