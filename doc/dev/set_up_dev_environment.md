# Local development

## Checkout the repository locally

```
cd c:\Instrument\Dev
git clone https://github.com/ISISComputingGroup/ibex_bluesky_core.git
```

## Create & activate a virtual environment (windows)

```
cd c:\Instrument\Dev\ibex_bluesky_core
python -m venv .venv
.venv\Scripts\activate
```

## Install the library & dev dependencies in editable mode
```
python -m pip install -e .[dev]
```
To run tests based on changes not yet in a release in the GUI PyDev console you will need to run this command using your global python install rather than in the venv.

## Unit tests
```
python -m pytest
```
> [!TIP]  
> To debug the tests in pycharm, use `--no-cov` as an additional option to your run configuration. There is a conflict [issue](https://youtrack.jetbrains.com/issue/PY-20186/debugging-of-py.test-does-not-stop-on-breakpoints-if-coverage-plugin-enabled) with the pytest-cov module which breaks the debugger.

## Run lints
```
ruff format --check
ruff check
pyright
```

## Build docs locally

To build the sphinx documentation locally run `sphinx-build doc _build` from the root of the repo. The generated output will be in the _build directory.

If you want to preview changes live, you can run `sphinx-autobuild doc _build --watch src` from the root of the repo instead which will start a local, hot-reloadable web server. This should rebuild the documentation whenever you change anything in src, which in turn will rebuild the API reference pages. 
