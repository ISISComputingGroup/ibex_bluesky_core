# Getting started

{py:obj}`ibex_bluesky_core` is a library which bridges the 
[IBEX control system](https://github.com/ISISComputingGroup/ibex_user_manual/wiki/What-Is-IBEX) 
and the [bluesky data acquisition framework](https://blueskyproject.io/).

Bluesky is a highly flexible data acquisition system, which has previously been used at
large-scale research facilities such as [NSLS-II](https://www.bnl.gov/nsls2/) and 
[Diamond](https://www.diamond.ac.uk/Home.html), along with many other large-scale scientific facilities.

While the bluesky framework itself is generic enough to cope with many forms of data acquisition,
one of the core use cases is "scanning" - that is, measuring how some experimental parameter(s) 
vary with respect to other parameter(s). Bluesky has extensive mechanisms and helpers for typical
scanning workflows.

The most important concepts in bluesky are:
- **Plans** tell bluesky what to do next, by emitting **Messages**
- The **RunEngine** executes plans by reacting to **Messages** (possibly interacting with devices)
- **Devices** encapsulate the details of how some specific device is controlled, reading or writing to EPICS PVs.
- **Callbacks** do something with the data produced during a scan (fitting, plotting, file-writing, ...)

## Plans

A plan is an _iterable_ of _messages_. A very simple plan, which doesn't do anything, is:

```python
from bluesky.utils import Msg

my_plan = [Msg("null")]
```

Where `Msg("null")` is an instruction to bluesky (which in this case, does nothing).

While it's possible to write bluesky plans as any iterable, in practice plans are usually written
using python [generators](https://peps.python.org/pep-0255/), using [python's 
`yield from` syntax](https://peps.python.org/pep-0380/) to delegate to other plans as necessary:

```python
import bluesky.plan_stubs as bps

def plan():
    yield from bps.null()
```

{ref}`Instrument-specific bluesky plans <where_are_plans_devices>` are defined in each instrument's `inst` scripts area.

## Devices

The {py:obj}`ibex_bluesky_core.devices` module provides built-in support for a number of ISIS-specific devices. For example,
blocks are available as devices:

```python
from ibex_bluesky_core.devices.block import block_r, block_mot

mot = block_mot("mot")  # An IBEX block pointing at a motor
det = block_r(float, "p5")  # A readback block with float datatype
```

Block objects provide several mechanisms for configuring write behaviour; see 
{py:obj}`~ibex_bluesky_core.devices.block.BlockWriteConfig` for detailed options.

Likewise, the DAE is available as a bluesky device: see [the DAE Documentation](../devices/dae.md)
for full examples including example configurations.

{ref}`Instrument-specific bluesky device instances <where_are_plans_devices>` are defined in each instrument's `inst` scripts area.

## Setting and reading values

Bluesky provides plan stubs for setting & reading values from bluesky devices: `bps.mv()` and 
`bps.rd()` respectively.

```python
from ibex_bluesky_core.devices.block import BlockMot
import bluesky.plan_stubs as bps

def multiply_motor_pos_by_2(mot: BlockMot):
    current_value = yield from bps.rd(mot)
    yield from bps.mv(mot, current_value * 2.0)
```

```{danger}
Notice that we are using `bps.rd()` and `bps.mv()` here, rather than `g.cget()` or `g.cset()`.
Bare `genie` or `inst` commands **must not** be used in bluesky plans - instead, prefer to use the
bluesky-native functionality - i.e. plans using `yield from`. 

Carefully review [calling external code](../plan_stubs/external_code.md) if you do need to call 
external code in a plan.

If, on the other hand, you need to run a plan as part of a larger script, see
{py:obj}`ibex_bluesky_core.run_engine.run_plan`.
```

For more details about plan stubs (plan fragments like `mv` and `read`), see the
[bluesky plan stubs documentation](https://blueskyproject.io/bluesky/main/plans.html#stub-plans)

## Scanning

Having created some simple devices, those devices can be used in standard bluesky plans:

```python
from ophyd_async.plan_stubs import ensure_connected
import bluesky.plans as bp
from ibex_bluesky_core.devices.block import block_r, block_mot

def my_plan(det_block_name: str, mot_block_name: str, start: float, stop: float, num: int):
    mot = block_mot(mot_block_name)
    det = block_r(float, det_block_name)

    # Devices connect up-front - this means that plans are generally "fail-fast", and
    # will detect problems such as typos in block names before the whole plan runs.
    yield from ensure_connected(det, mot, force_reconnect=True)
    
    # Delegate to bluesky's scan plan.
    yield from bp.scan([det], mot, start, stop, num)
```

For details about plans which are available directly from `bluesky` - like `bp.scan` above - see 
[bluesky's plan documentation](https://blueskyproject.io/bluesky/main/plans.html#pre-assembled-plans).

## The `RunEngine`

The `RunEngine` is the central "conductor" in bluesky - it is responsible for reading a plan and
performing the associated actions on the hardware. To get a run engine instance, use:

```python
from ibex_bluesky_core.run_engine import get_run_engine
RE = get_run_engine()
```

```{tip}
In the IBEX GUI, manually getting a runengine is unnecessary - it is done automatically.
```

Then execute a plan using the `RunEngine`:

```python
RE(my_plan("det", "mot", 0, 10, 5))
```

Note that typing `my_plan("det", "mot", 0, 10, 5)` does not do anything by itself. 
That is because `my_plan` is a python generator - which does nothing until iterated. 
To actually execute the plan, it must be passed to the [`RunEngine`](ibex_bluesky_core.run_engine), which is conventionally 
called `RE`.

For more detail about the [`RunEngine`](ibex_bluesky_core.run_engine), see:
- {py:obj}`ibex_bluesky_core.run_engine.get_run_engine`
- {external+bluesky:ref}`tutorial_run_engine_setup`
- {external+bluesky:doc}`run_engine_api`

## Callbacks

Callbacks are bluesky's mechanism for listening to data from a scan. Some examples of common callbacks
are:
- [File writing](../callbacks/file_writing.md)
- [Plotting](../callbacks/plotting.md)
- [Fitting](/callbacks/fitting/fitting.md)
- [Live Tables](https://blueskyproject.io/bluesky/main/callbacks.html#livetable)

It is possible to use callbacks manually, when executing a plan:

```python
from bluesky.callbacks import LiveTable

RE(my_plan("det", "mot", 0, 10, 5), LiveTable(["mot", "det"]))
```

However, to save typing out callbacks repeatedly, user-specified plans can add callbacks from within a plan, using
{external+bluesky:py:obj}`bluesky.preprocessors.subs_decorator`:

```python
from ibex_bluesky_core.devices.block import block_r, block_mot
from ophyd_async.plan_stubs import ensure_connected
from bluesky.preprocessors import subs_decorator
from bluesky.callbacks import LiveTable
import bluesky.plans as bp

def my_plan(det_block_name: str, mot_block_name: str, start: float, stop: float, num: int):
    mot = block_mot(mot_block_name)
    det = block_r(float, det_block_name)

    @subs_decorator([
      LiveTable([mot.name, det.name]),
    ])
    def _inner():
      yield from ensure_connected(det, mot, force_reconnect=True)
      yield from bp.scan([det], mot, start, stop, num)
    yield from _inner()
```

The above will show a {external+bluesky:ref}`livetable` by default, any time `my_plan` is executed. The same mechanism can
be used to always configure a scan with plots and a fit with a specific type.

This library includes a standard callbacks collection, {py:obj}`~ibex_bluesky_core.callbacks.ISISCallbacks`, which should suit the needs of many simple scans. This includes the ability to fit, plot, add human-readable file output and show a live table of scanned fields. See {ref}`icc` on how to use this.

For more general information on callbacks, see the
{external+bluesky:doc}`bluesky callbacks documentation <callbacks>`.

## Metadata

Bluesky provides a number of mechanisms for inserting metadata into a scan. In general, metadata may be any JSON-serialisable object including numbers, strings, lists, dictionaries, and nested combinations of those. The bluesky documentation has an {external+bluesky:doc}`extensive description of metadata mechanisms <metadata>`, but the main options are summarised below.

**Persistently (for this python session)**
```python
RE.md["user"] = "Tom"
RE.md["sample"] = "unobtainium"
```

**For one `RE` call**:
```python
RE(some_plan(), sample="unobtainium", user="Tom")
```

**Dynamically, within a plan (using {external+bluesky:py:obj}`bluesky.preprocessors.inject_md_wrapper`)**
```python
import bluesky.plan_stubs as bps
from bluesky.preprocessors import inject_md_wrapper


def some_plan(dae):
    run_number = yield from bps.rd(dae.current_or_next_run_number_str)
    return (yield from inject_md_wrapper(subplan(), {"run_number": run_number}))
```

**Dynamically, within a plan (using {external+bluesky:py:obj}`bluesky.preprocessors.inject_md_decorator`)**
```python
import bluesky.plan_stubs as bps
from bluesky.preprocessors import inject_md_decorator


def some_plan(dae):
    run_number = yield from bps.rd(dae.current_or_next_run_number_str)
    
    @inject_md_decorator({"run_number": run_number})
    def _inner():
        yield from subplan()

    yield from _inner()
```

In addition to the above mechanisms, many built-in bluesky plans (such as {external+bluesky:py:obj}`bluesky.plans.scan` and {py:obj}`ibex_bluesky_core.plans.scan`) take an `md` keyword argument, which can also be used to insert additional metadata for one scan.

## See also

**Plans & plan-stubs**
- Bluesky {external+bluesky:doc}`plans` 
- Bluesky {external+bluesky:ref}`stub_plans` 
- {py:obj}`ibex_bluesky_core.plans`
- {py:obj}`ibex_bluesky_core.plan_stubs`

**Callbacks**
- Bluesky {external+bluesky:doc}`callbacks`
- {py:obj}`ibex_bluesky_core.callbacks`
- {doc}`Fitting Callbacks </callbacks/fitting/fitting>`

**Full Examples**
- [Manual system tests](https://github.com/ISISComputingGroup/ibex_bluesky_core/tree/main/manual_system_tests) (full, 
runnable example plans)

**External documentation**
- {external+bluesky:doc}`bluesky user documentation <userindex>`
- {external+ophyd_async:doc}`ophyd_async tutorials <tutorials>`
