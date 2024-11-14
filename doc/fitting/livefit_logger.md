# Fitting Files Callback
## Fitting Files

The callback (`LiveFitLogger`) exists to write all fitting metrics from `LiveFit` to file.

This callback provides you with useful metrics such as `R-squared` and `chi-square`, then providing you with a table of the raw collected data included modelled `y` data and `y` uncertainty. 

### Example
An example of using this could be: 

```{code} python
def some_plan() -> Generator[Msg, None, None]:
    ... # Set up prefix, reducers, controllers etc. here
    block = block_rw_rbv(float, "mot")

    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    lf = LiveFit(
        Linear.fit(), y=reducer.intensity.name, x=block.name
    )

    yield from ensure_connected(block, dae, force_reconnect=True)

    @subs_decorator(
        [
            LiveFitLogger(
                lf,
                y=reducer.intensity.name,
                x=block.name,
                output_dir=Path(f"C:\\Instrument\\Var\\logs\\bluesky\\fitting"),
                yerr=reducer.intensity_stddev.name
            )
            ... # Other callbacks ie. live table/plot here - you can use multiple!
        ]
    )
    def _inner() -> Generator[Msg, None, None]:
        num_points = 3
        yield from bps.mv(dae.number_of_periods, num_points)
        yield from bp.scan([dae], block, 0, 10, num=num_points)

    yield from _inner()

RE = get_run_engine()
RE(some_plan())
```

This will put the all fitting data collected over the run into a `.csv` file, named after the `uid` of the scan, in the `C:\\Instrument\\Var\\logs\\bluesky\\fitting` path provided to the callback. You may also provide a `postfix` to append to the end of the filename to avoid overwriting fitting files.
