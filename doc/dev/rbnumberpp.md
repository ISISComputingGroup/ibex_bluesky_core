# RB Number injection preprocessor

A {external+bluesky:ref}`plan preprocessor <preprocessors>` exists for the run engine to inject the current RB number into all bluesky start documents. This is added to the run engine by default, but to remove this from a plan you should just need to do 

```{code}
RE.preprocessors.pop()
```

Which will remove it. 
