# RB Number injection preprocessor

A [preprocessor](https://nsls-ii.github.io/bluesky/plans.html#plan-preprocessors) exists for the run engine to inject the current RB number into all bluesky start documents. This is added to the run engine by default, but to remove this from a plan you should just need to do 

```{code}
RE.preprocessors.pop()
```

Which will remove it. 
