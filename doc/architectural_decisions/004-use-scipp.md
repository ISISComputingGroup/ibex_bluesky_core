# Use `scipp`

## Status

Current

## Context

A decision needs to be made about whether to use scipp, numpy, uncertainties or develop our own library for the purpose of providing support for generating uncertanties on our counts data.

# Decision

We will be using scipp.

# Justification & Consequences

- `scipp` is being developed at ESS with past input from STFC, so is well suited for neutron counts data.
- `scipp` has a `numpy`-like interface but handles units and uncertainties by default under-the-hood.
- Neither `numpy` or `uncertanties` have exactly the functionality we would need, so the solution using them would be a mix of the libraries and our own code, there would be more places to go wrong. Maintainability.
- Developing our own uncertainties library will take time to understand and then implement. All of the functionality that we need has been done beforehand, so better to not waste time & effort.