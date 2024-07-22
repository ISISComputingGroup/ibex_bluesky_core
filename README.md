# ibex_bluesky_core

Core bluesky plan stubs &amp; devices for use at ISIS. Not instrument/technique specific.

### Local development

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

Run lints:
```
ruff format --check
ruff check
pyright
```
