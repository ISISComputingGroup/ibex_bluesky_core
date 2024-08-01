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

### Release Process

Releases are created automatically via a github action, to create a release just create a new git tag on the commit on main (i.e. `git pull`, `git checkout main` `git tag <release.version.number.` `git push origin tag <release.version.number.`) This will start a workflow that will check that all linters and tests pass, and then publish a new release with the version number specified in the tag to [Pypi](https://pypi.org/project/ibex-bluesky-core/0.0.1/) and github. The new release can then be installed via `pip install ibex_bluesky_core`. The workflow must be approved by someone in the ICP-Write group.

Credentials for Pypi can be found on keeper.
