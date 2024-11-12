# Use `ophyd-async`

## Status

Current

## Context

We need to decide whether to use `ophyd` or `ophyd-async` as our bluesky
device abstraction layer.

`ophyd` has been the default device abstraction layer for bluesky EPICS devices for
some time.

`ophyd-async` is a newer (and therefore less mature) device abstraction layer, 
with similar concepts to `ophyd`. It has been implemented primarily by DLS.

The *primary* differences are:
- In `ophyd-async` many functions are implemented as `asyncio` coroutines.
- `ophyd-async` has better support for non-channel-access backends (notably, PVA)
- Reduction in boilerplate

## Present

Tom & Kathryn

## Decision

We will use `ophyd-async`.

## Consequences

- `ophyd-async` will allow us to use PVAccess easily.
- `ophyd-async` will allow us to do fly scanning, if required in future, more easily than `ophyd`
- Developers will need to understand more details about `asyncio`
- Developers will have to write somewhat less boilerplate code in `ophyd-async` as compared to `ophyd`
- Our devices should be more comparable to other facilities on site (e.g. DLS) who are using `ophyd-async`.