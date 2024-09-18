# Waiters

A `waiter` defines an arbitrary strategy for how long to count at each point.

Some waiters may be very simple, such as waiting for a fixed amount of time or for a number
of good frames or microamp-hours. However, it is also possible to define much more 
sophisticated waiters, for example waiting until sufficient statistics have been collected.

## GoodUahWaiter

Waits for a user-specified number of microamp-hours.

Published signals:
- `simpledae.good_uah` - actual good uAh for this run.

## GoodFramesWaiter

Waits for a user-specified number of good frames (in total for the entire run)

Published signals:
- `simpledae.good_frames` - actual good frames for this run.

## GoodFramesWaiter

Waits for a user-specified number of good frames (in the current period)

Published signals:
- `simpledae.period.good_frames` - actual period good frames for this run.

## MEventsWaiter

Waits for a user-specified number of millions of events

Published signals:
- `simpledae.m_events` - actual period good frames for this run.

## TimeWaiter

Waits for a user-specified time duration, irrespective of DAE state.

Does not publish any additional signals.
