# Simple Dae

The `SimpleDae` class is designed to be a configurable DAE object, which will cover the
majority of DAE use-cases within bluesky.

This class uses several objects to configure its behaviour:
- The `Controller` is responsible for beginning and ending acquisitions.
- The `Waiter` is responsible for waiting for an acquisition to be "complete".
- The `Reducer` is responsible for publishing data from an acquisition that has 
  just been completed.

This means that `SimpleDae` is generic enough to cope with most typical DAE use-casess, for
example running using either one DAE run per scan point, or one DAE period per scan point.

For complex use-cases, particularly those where the DAE may need to start and stop multiple 
acquisitions per scan point (e.g. polarization measurements), `SimpleDae` is unlikely to be 
suitable; instead the `Dae` class should be subclassed directly to allow for finer control.

## Mapping to bluesky device model

### Start of scan (`stage`)

`SimpleDae` will call `controller.setup()` to allow any pre-scan setup to be done.

For example, this is where the period-per-point controller object will begin a DAE run.

### Each scan point (`trigger`)

`SimpleDae` will call:
- `controller.start_counting()` to begin counting for a single scan point.
- `waiter.wait()` to wait for that acquisition to complete
- `controller.stop_counting()` to finish counting for a single scan point.
- `reducer.reduce_data()` to do any necessary post-processing on 
  the raw DAE data (e.g. normalization)

### Each scan point (`read`)

Any signals marked as "interesting" by the controller, reducer or waiter will be published
in the top-level documents published when `read()`ing the `SimpleDae` object.

These may correspond to EPICS signals directly from the DAE (e.g. good frames), or may be 
soft signals derived at runtime (e.g. normalized intensity).

This means that the `SimpleDae` object is suitable for use as a detector in most bluesky
plans, and will make an appropriate set of data available in the emitted documents.

### End of scan (`unstage`)

`SimpleDae` will call `controller.teardown()` to allow any post-scan teardown to be done.

For example, this is where the period-per-point controller object will end a DAE run.