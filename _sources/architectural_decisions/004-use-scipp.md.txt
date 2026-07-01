# 4. Use `scipp`

## Status

Current

## Context

We need to choose a library which helps us to transform "raw" neutron or muon data from the DAE, into processed
quantities that we scan over.

Desirable features include:
- Uncertainty propagation, following standard uncertainty propagation rules. While this could apply to any data in
principle, it will be especially relevant for neutron/muon counts data.
- Unit handling & conversions
  - Simple unit conversions, like microns to millimetres.
  - Neutron-specific unit conversions, like time-of-flight to wavelength
- Ability to handle the typical types of data we would acquire from the DAE and process as part of a scan:
  - Histograms of neutron/muon counts
  - N-dimensional arrays
  - Event-mode data (in future)

Candidate solutions include:

- `mantid`
- `scipp`
- `uncertainties`
- `numpy` + home-grown uncertainty-propagation

## Decision

- Default to using `scipp` for most cases
- Explore using `mantid` via autoreduction APIs, where we need to do more complex reductions

## Justification & Consequences

### `numpy`

Using `numpy` by itself is eliminated on the basis that we would need to write our own uncertainty-propagation code,
which is error prone.

`numpy` by itself may still be used in places where uncertainty propagation is not needed.

### `uncertainties`

The `uncertainties` package tracks correlations so may have bad scaling on "large" arrays, where correlation matrices
can become large in some cases. Would need to be combined with another library, e.g. `pint`, in order to also support
physical units. No neutron-specific functionality.

### `mantid`

Mantid is not easily installable (e.g. via `pip` at present).

While we have a way to call out to mantid via a REST API, initial tests have shown that the latency of this approach
is around 15 seconds. This means it is unsuitable for many types of scans, for example alignment scans, where count
times are far lower than 15 seconds.

However, for complex reductions, we should still consider the option of passing data out to mantid. This is especially
true if reductions depend significantly on instrument geometry, on instrument-specific corrections, or on other details
for which mantid is best-equipped to deal with.

Calling out to mantid via an API should also be considered if a reduction step may use significant compute resource.

### `scipp`

`scipp` will be our default way of taking raw data from the DAE and processing it into a scanned-over quantity.

However, in cases where the reduction is expensive (in terms of compute cost) or complex (either implementation, or
in terms of required knowledge of geometry/instrument-specific corrections), then we should consider using mantid via
the autoreduction API in those cases instead.
