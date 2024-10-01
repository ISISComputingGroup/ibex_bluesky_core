# Run in-process

## Status

Current

## Context

`bluesky` code can be run in several ways:
- By the user at an interactive shell, directly calling the run engine in-process.
- By a central worker process, to which the user would "submit" plans to run.
  - See DLS's `blueapi` for an example of a REST API for submitting plans to the run engine.

## Present

Tom & Kathryn

## Decision

We will run bluesky plans in-process for now, while not _excluding_ the possibility
that they could be run behind a worker process at some point in future.

## Consequences

- We will not, at least initially, have to write or use an extra worker process.
- Users will have the ability to call the run engine directly
  - This gives us more flexibility initially
  - Makes plotting easier
  - `bluesky` code will be less isolated from anything else running in-process