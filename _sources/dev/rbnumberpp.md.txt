# RB Number injection preprocessor

A {external+bluesky:ref}`plan preprocessor <preprocessors>` exists for the run engine to inject the current RB number into all bluesky start documents. This is added to the run engine by default, but to remove this from the {py:obj}`~bluesky.run_engine.RunEngine`, use:

```python
RE.preprocessors.pop()
```
