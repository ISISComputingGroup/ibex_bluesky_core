# Troubleshooting

## Where is ...?

### Instrument-specific plans & devices

This is located in each instrument's `inst` script area, with their other instrument-specific scripts.

`c:\Instrument\Settings\config\NDX<inst>\configurations\Python\inst\bluesky`.

Instrument-specific bluesky plans will typically be defined in the `plans` module in the above area, and devices will 
be defined in a `devices` module.

### This library (`ibex_bluesky_core`)

In a clean installation of IBEX, `ibex_bluesky_core` is installed as a python module via pip into the
[uktena](https://github.com/IsisComputingGroup/uktena) environment which is in `c:\instrument\apps\python3`.

However, for instruments which have been testing bluesky and may have versions of `ibex_bluesky_core` with local
modifications, a version of `ibex_bluesky_core` may be checked out into `c:\instrument\dev\ibex_bluesky_core` on the
instrument, and this will have been editable-installed into the `uktena` environment.

### Other bluesky libraries (`ophyd_async`, `bluesky`, ...)

`ophyd_async` and `bluesky` are installed as python modules. via pip, into the
[uktena](https://github.com/IsisComputingGroup/uktena) environment which is in `c:\instrument\apps\python3` because
they are specified in `pyproject.toml` of `ibex_bluesky_core`, which itself is a dependency of `uktena`.

### Logs

Log files are stored in `C:\Instrument\Var\logs\bluesky`.

```{note}
Older log files will be moved by the log rotation script to 
`<isis share>\inst$\Backups$\stage-deleted\ndx<instrument>\Instrument\Var\logs\bluesky`
```

The default log level is `INFO` and all messages from `ibex_bluesky_core`, `bluesky` and `ophyd_async` are captured.

If you need to increase this to `DEBUG` to isolate an issue, you can do so using 
{py:obj}`ibex_bluesky_core.log.set_bluesky_log_levels`. See [logging documentation](logging.md) for a full example
showing how to do this.

### Scientist-facing data

Scientist-facing output files are written to `<isis share>\inst$\NDX<inst>\user\test\scans\<current rb number>` by 
default.

Custom file-output paths can be specified by passing extra arguments to 
{py:obj}`HumanReadableFileCallback<ibex_bluesky_core.callbacks.HumanReadableFileCallback>` 
for the "human-readable" files, or 
{py:obj}`LiveFitLogger<ibex_bluesky_core.callbacks.LiveFitLogger>` 
for the fit output files. These callbacks may be hidden behind
{py:obj}`ISISCallbacks<ibex_bluesky_core.callbacks.ISISCallbacks>` which also allows specifying output paths.

See [dae_scan manual system test](https://github.com/ISISComputingGroup/ibex_bluesky_core/blob/0.2.1/manual_system_tests/dae_scan.py#L83)
for an example of how to configure these output paths using {py:obj}`ISISCallbacks<ibex_bluesky_core.callbacks.ISISCallbacks>`.

### Raw diagnostic data

Raw documents emitted by bluesky are stored in `C:\Instrument\Var\logs\bluesky\raw_documents` - these show the raw 
data emitted by bluesky scans. The filenames in this directory correspond to bluesky's scan ID, which is printed to 
the console at the end of each scan, and is also included as metadata in the scientist-facing output files.

These files are written by {py:obj}`ibex_bluesky_core.callbacks.DocLoggingCallback`, which is subscribed
to the run engine by default in {py:obj}`ibex_bluesky_core.run_engine.get_run_engine`.

```{note}
Older raw documents will be moved by the log rotation script to 
`<isis share>\inst$\Backups$\stage-deleted\ndx<instrument>\Instrument\Var\logs\bluesky\raw_documents`
```

---

## How do I ...?

### Run a plan

To run a plan, you need to pass it to the `RE` object, which is made for you by default, as an initialisation command,
in IBEX GUI versions later than 2025.2. 

:::{tip}
For versions of the GUI earlier than 2025.2, where the run engine is not created automatically, an `RE` object can be 
made manually using
```python
from ibex_bluesky_core.run_engine import get_run_engine
RE = get_run_engine()
```
:::

For example, to run a plan, use:

```
>>> RE(some_clever_plan(which, takes, some, arguments))
```

Note that without the `RE(...)` call, the plan **does nothing**:

```
>>> some_clever_plan(which, takes, some, arguments)
<generator object scan at 0x000002286311D080>
```

### Pause/stop/resume/abort a plan

While a plan is running, a single ctrl-c will stop gracefully after the next point has finished counting. A message
like the following will be printed:

> A 'deferred pause' has been requested. The RunEngine will pause at the next checkpoint. 
> To pause immediately, hit Ctrl+C again in the next 10 seconds.
> Deferred pause acknowledged. Continuing to checkpoint.

Two ctrl-c keystrokes within 10 seconds of each other will stop the plan immediately.

When a plan is paused, you will get a short exception message with a summary of your options:

```
Pausing...
Traceback (most recent call last):
  File "C:\Instrument\Apps\Python3\Lib\site-packages\IPython\core\interactiveshell.py", line 3579, in run_code
    exec(code_obj, self.user_global_ns, self.user_ns)
  File "<ipython-input-27-288a69b9f38e>", line 1, in <module>
    RE(bps.sleep(999))
  File "C:\Instrument\Apps\Python3\Lib\site-packages\bluesky\run_engine.py", line 976, in __call__
    raise RunEngineInterrupted(self.pause_msg) from None
bluesky.utils.RunEngineInterrupted: 
Your RunEngine is entering a paused state. These are your options for changing
the state of the RunEngine:

RE.resume()    Resume the plan.
RE.abort()     Perform cleanup, then kill plan. Mark exit_stats='aborted'.
RE.stop()      Perform cleanup, then kill plan. Mark exit_status='success'.
RE.halt()      Emergency Stop: Do not perform cleanup --- just stop.
```

At this point, you will be returned to an interactive shell. You must choose one of these options above before 
attempting further operations with the `RunEngine`.

- `RE.resume()` - resumes the scan from the point at which it was interrupted. The plan will complete as usual.
- `RE.stop()` and `RE.abort()` are functionally identical - the plan will gracefully terminate, including running any
cleanup actions and calling registered callbacks.
- `RE.halt()` tells the RunEngine to drop dead and not do **anything** on the way out. This includes cleanup handlers,
which for example may return motors to sensible positions or return DAE configuration to a state in which data can be
taken.

If you are unsure exactly what state your `RunEngine` is in, `RE.state` can be used to check this. If you attempt to 
run another plan before choosing one of the options above, you will get an exception like:

```
Traceback (most recent call last):
  File "C:\Instrument\Apps\Python3\Lib\site-packages\IPython\core\interactiveshell.py", line 3579, in run_code
    exec(code_obj, self.user_global_ns, self.user_ns)
  File "<ipython-input-29-288a69b9f38e>", line 1, in <module>
    RE(bps.sleep(999))
  File "C:\Instrument\Apps\Python3\Lib\site-packages\bluesky\run_engine.py", line 920, in __call__
    raise RuntimeError(f"The RunEngine is in a {self._state} state")
RuntimeError: The RunEngine is in a paused state
```

This means that you still need to choose how to continue from the previous interruption.

### Get the result of a plan

A plan will return a `RunEngineResult` object, which has a `plan_result` attribute:

```
result = RE(some_plan())
result.plan_result
```

If a plan was interrupted and resumed later, the result is returned by the `RE.resume()` call:

```
RE(some_plan())
<KeyboardInterrupt>
result = RE.resume()
result.plan_result
```

```{tip}
If the result wasn't captured, it's still possible to access it in an IPython interactive shell using the special 
underscore variables, for example `result = _`.

This is not specific to bluesky - it's an IPython feature where `_` is bound to the return value of the last expression,
`__` is bound to the result of the second-to-last expression, and so on.
```

[Do not try to "hide" the `RunEngine` in a script/function](https://blueskyproject.io/bluesky/main/tutorial.html#plans-in-series).
The `RE(...)` call should always be typed by the user, at the terminal.

### Connect a device

Bluesky plans need devices to be connected up-front. This is so that errors (such as PVs not existing) are detected
as soon as possible, not mid-way through a scan.

Top-level plan wrappers should use the `ensure_connected` plan stub from `ophyd_async`:

```python
from ophyd_async.plan_stubs import ensure_connected


def top_level_plan(dae, block):
    yield from ensure_connected(dae, block)
    yield from scan(...)
```

If you forget to do this, you will get a stack trace containing:

```
NotImplementedError: No PV has been set as connect() has not been called
```

### Debug `NotConnected` errors

If `ophyd_async` cannot connect to a PV, you will get an error that looks like:

```
sample_changer2: NotConnected:
    readback: NotConnected: ca://TE:NDW2922:CS:SB:sample_changer2
```

In the first instance, check that the relevant PV exists if you get it via `caget`.

If the device is a {py:obj}`block_rw<ibex_bluesky_core.devices.block.BlockRw>`, but the `:SP` record does not exist,
you may use a `block_w` instead. This will both read and write to the same PV. Similarly, if `blockname:SP:RBV` does
not exist, a {py:obj}`block_rw_rbv<ibex_bluesky_core.devices.block.BlockRwRbv>` cannot be used.

If the device is a {py:obj}`ibex_bluesky_core.devices.reflectometry.ReflParameter` and `redefine` fails to connect,
pass `has_redefine=False` when constructing that parameter (this means you won't be able to redefine the position
of this refl parameter).

If instead you get a `TypeError` that looks like:

```
sample_changer: NotConnected:
    readback: TypeError: TE:NDW2922:CS:SB:sample_changer with inferred datatype float cannot be coerced to str
```

This is because the **datatype of the underlying PV** does not match the **declared type in bluesky**. `ophyd_async`
will not allow you to connect a `block_r(str, "some_block")` if `"some_block"` is a float-type PV. Every signal in
`ophyd_async` is strongly typed.

### Change how `set` on a device behaves

For a {py:obj}`writable block<ibex_bluesky_core.devices.block.BlockRw>`, a `write_config` argument can be specified. 
See the options on {py:obj}`BlockWriteConfig<ibex_bluesky_core.devices.block.BlockWriteConfig>` for detailed options. These are specified
when first creating the `block` object, which is likely to be in 
`\Instrument\Settings\config\NDX<inst>\configurations\Python\inst\bluesky\devices.py`, or dynamically created as part
of a wrapper plan. See [block documentation](../devices/blocks.md) for detailed documentation about how to set up block
devices.

For complex cases, where a `set` being complete depends on multiple conditions, a custom `ophyd_async` device is usually
the cleanest way to accomplish this. These can be defined in an instrument's `inst` scripts area if they are specific
to one instrument, or can be promoted to `ibex_bluesky_core` if generally useful.

### Add extra sleeps into a plan

Generally you should not need to insert sleeps at the *plan* level - prefer instead to modify *devices* so that they
accurately report when they have finished setting (including any necessary settle times, for example). Writable blocks 
have a {py:obj}`BlockWriteConfig<ibex_bluesky_core.devices.block.BlockWriteConfig>` which has a `settle_time_s` 
parameter for this purpose.

If you *really* need to sleep in a plan, rather than at the device level, use `yield from bps.sleep(duration_seconds)`.
Do **not** just call `time.sleep()` in a plan - this will stall the event loop and interfere with keyboard interrupts, 
for example.

### Add exception-handling to a plan

In plans, because they are generators, you cannot just use `try-finally` or `try-except`.

Instead, bluesky provides wrappers that implement error handling: 
[`finalize_wrapper`](https://blueskyproject.io/bluesky/main/generated/bluesky.preprocessors.contingency_wrapper.html#bluesky.preprocessors.contingency_wrapper)
and 
[`contingency_wrapper`](https://blueskyproject.io/bluesky/main/generated/bluesky.preprocessors.finalize_wrapper.html#bluesky.preprocessors.finalize_wrapper).

### Debug DAE failing to begin

Check the DAE can begin a run without using bluesky.

If you are counting using periods, and using the spectrum-data map, this imposes a limit of {math}`5000000` on number of
`periods * (spectra+1) * (time channels+1)`. This means that scans with high numbers of points may fail, where those 
with fewer points will work.

### Debug a failed fit

Fitting will only ever start after at least as many points have been collected, as there are free parameters in the
fitting model. For example, a guassian fit will not be attempted with less than 4 data points. This can occur if a
scan is interrupted early, for example.

Fits can also fail if the data is particularly poor.

### Debug a bad fit

Consider whether you can use a different fitting model. Some models are more prone to getting stuck in local minima than
others.

For peak-like data, `"com"` or `"max"` from bluesky's 
[`PeakStats callback`](https://blueskyproject.io/bluesky/main/callbacks.html#peakstats) can robustly give *an* answer,
although often this will not be as good as a full fit and may not always be appropriate.

### Debug keyboard-interrupt problems

If a double ctrl-c does nothing, this is probably because the event loop is stalled - which is likely the  result of a 
plan or device doing I/O or other synchronous operations directly, rather than via `asyncio` or `yield from`. 

Find the offending function and replace it with it's bluesky-native equivalent. Python's `asyncio` module has a debug 
mode which warns on long-running tasks - this can help identify the offending call.

---

## What is this syntax ...?

### `async def` / `await` / `asyncio`

Functions declared as `async def` are [python **coroutines**](https://docs.python.org/3/library/asyncio-task.html#).

In a bluesky context, if you see an `async def` function, it is likely that you are looking at either
an `ophyd_async` device class, or a `RunEngine` message handler.

In order to get the result of a coroutine, it needs to be `await`ed:

```python
async def foo():
    result = await some_coroutine()
```

In an `async def` function, do not perform blocking operations. For example, always use `await asyncio.sleep()`,
and not `time.sleep()`. Similarly, do not use synchronous functions which perform I/O from a coroutine (e.g. calling
`genie` APIs) - use the `async` APIs provided by `ophyd_async` instead.

As a general rule of thumb, any function that could reasonably take more than a few tens of milliseconds, should not be
called directly from a coroutine.

### `yield` / `yield from` / `Generator`

Functions containing `yield` and/or `yield from` are [python **generators**](https://wiki.python.org/moin/Generators). 

If you see `yield from` in a function, you are likely to be looking at a
[bluesky plan](https://blueskyproject.io/bluesky/main/plans.html#).

`yield from` is the syntax used to delegate to subplans:

```python
def some_plan():
    yield from move(...)
    yield from scan(...)
```

Will perform an initial move followed by a scan.

Return values from plans can be captured:

```python
def plan_that_returns():
    yield from something()
    return "hello, world"

def plan():
    returned_value = yield from plan_that_returns()
```

Like `coroutines` above, long-running functions or functions which perform I/O should not be used in plans. Doing so
can stall the `RunEngine`'s internal event loop, break keyboard-interrupts, and break rewindability. Use bluesky-native
functionality instead - for example:
- [`yield from bps.sleep()`](https://blueskyproject.io/bluesky/main/generated/bluesky.plan_stubs.sleep.html#bluesky.plan_stubs.sleep) instead of `time.sleep()`
- [`yield from bps.mv(block_object, value)`](https://blueskyproject.io/bluesky/main/generated/bluesky.plan_stubs.mv.html#bluesky.plan_stubs.mv) instead of `g.cset(block_name, value)`
- [`value = yield from bps.rd(block_object)`](https://blueskyproject.io/bluesky/main/generated/bluesky.plan_stubs.rd.html#bluesky.plan_stubs.rd) instead of `value = g.cget(block_name)["value"]`

If you must call an external function which may be long running or do I/O from a plan, review 
[call_sync](../plan_stubs/external_code).
