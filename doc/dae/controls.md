# Controlling the DAE directly

It is possible to control the DAE directly using the signals provided by `dae.controls`.

The intention is that these signals should be used by higher-level _devices_, rather than being
used by plans directly.

For example, beginning a run is possible via `dae.controls.begin_run.trigger()`.

## Advanced options

Options on `begin` (for example, beginning a run in paused mode) can be specified
using the `dae.controls.begin_run_ex` signal.

Unlike the standard `begin_run` signal, this needs to be `set()` rather than simply
`trigger()`ed, the value on set is a combination of flags from `BeginRunExBits`.
