### Local development

Checkout the repository locally

```
cd c:\Instrument\Dev
git clone https://github.com/ISISComputingGroup/ibex_bluesky_core.git
```

Create & activate a python virtual environment (windows):

```
python -m venv .venv
.venv\Scripts\activate
```

Install the library & dev dependencies in editable mode:
```
python -m pip install -e .[dev]
```

Run the unit tests:
```
python -m pytest
```
> [!TIP]  
> To debug the tests in pycharm, use `--no-cov` as an additional option to your run configuration. There is a conflict [issue](https://youtrack.jetbrains.com/issue/PY-20186/debugging-of-py.test-does-not-stop-on-breakpoints-if-coverage-plugin-enabled) with the pytest-cov module which breaks the debugger.

Run lints:
```
ruff format --check
ruff check
pyright
```

Run the 'demo' plan:

```
python -c "from ibex_bluesky_core.demo_plan import run_demo_plan;run_demo_plan()"
```

If PVs for the demo plan don't connect, ensure that:
- Set MYPVPREFIX
```
set MYPVPREFIX=TE:NDWXXXX:
```
- You have set an `EPICS_CA_ADDR_LIST`:
```
set "EPICS_CA_ADDR_LIST=127.255.255.255 130.246.51.255"
set "EPICS_CA_AUTO_ADDR_LIST=NO"
```
- You have an IBEX server running with a DAE in setup state, which can begin a simulated run
- You have a readable & writable block named "mot" in the current configuration pointing at 
the type of block expected by `run_demo_plan`