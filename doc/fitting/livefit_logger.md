# Fitting Files Callback
## Fitting Files

The callback ([`LiveFitLogger`](ibex_bluesky_core.callbacks.fitting.livefit_logger)) exists to write all fitting metrics from [`LiveFit`](ibex_bluesky_core.callbacks.fitting.LiveFit) to file. These are designed to be human readable files rather than machine readable.

This callback provides you with useful metrics such as `R-squared` and `chi-square`, then providing you with a table of the raw collected data included modelled `y` data and `y` uncertainty. 

### Example
An example of using this could be: 

```{code} python
def some_plan() -> Generator[Msg, None, None]:
    ... # Set up prefix, reducers, controllers etc. here

    @subs_decorator(
        [
            LiveFitLogger(
                lf, # LiveFit
                y=reducer.intensity.name,
                x=block.name,
                output_dir=Path(f"C:\\Instrument\\Var\\logs\\bluesky\\fitting"),
                postfix="bob" # Make sure to have different postfixes if using 
                    # more than 1 LiveFitLogger per run
                yerr=reducer.intensity_stddev.name, # Not required
            )
            ... # Other callbacks ie. live table/plot here - you can use multiple!
        ]
    )
    def _inner() -> Generator[Msg, None, None]:
        ... # Continue to plan
```

This will put the all fitting data collected over the run into a `.csv` file, named after the `uid` of the scan, in the `C:\\Instrument\\Var\\logs\\bluesky\\fitting` path provided to the callback. You should provide a `postfix` to append to the end of the filename to disambiguate different fits and to avoid overwriting fitting files- it is only one file per fit completed.

If you provide a signal name for the `yerr` argument then an extra column for `y uncertainty` will be displayed in the fitting file. You have the option to not provide anything for this argument if you do not want to have uncertainty information in your fitting file. Keep in mind that even if you provide `yerr` in [`LiveFitLogger`](ibex_bluesky_core.callbacks.fitting.livefit_logger), you will still need to provide `yerr` in [`LiveFit`](ibex_bluesky_core.callbacks.fitting.LiveFit) if you want uncertainty/weight per point to influence the fit. 
