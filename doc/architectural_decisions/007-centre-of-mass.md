# Using our own Centre of Mass Callback

## Status

Current

## Context

A decision needs to be made about whether to make changes to upstream Bluesky so that their `CoM` callback works for us, or we make our own.

## Decision

We will be making our own `CoM` callback.

## Justification & Consequences

We attempted to make changes to upstream Bluesky which were rejected, as it adds limits to the functionality of the callback. We also found other limitations with using their callback, such as not being able to have disordered and non-continuous data sent to it without it skewing the calculated value- we need it to work with disordered and non-continuous data as we need to be able to run continuous scans.

This will mean that...
- Our version of the callback will not be supported by Bluesky and may need changes as Bluesky updates.
- We can have a version of the callback that is made bespokely for our use cases.