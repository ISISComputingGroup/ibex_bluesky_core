{#livefit_logger}
# Saving fit results to file ({py:obj}`~ibex_bluesky_core.callbacks.LiveFitLogger`)

The {py:obj}`~ibex_bluesky_core.callbacks.LiveFitLogger` callback exists to write the results of a {py:obj}`~ibex_bluesky_core.callbacks.LiveFit` to file. These are designed to be human-readable files, rather than machine readable.

The files written by this callback contain:
- The result of an {py:obj}`lmfit.model.ModelResult.fit_report`, which contains fit statistics such as r-squared, optimized values of fit parameters, and information about correlations if present.
- Two blank lines
- A csv table containing `x`, `y`, optionally `y` uncertainty, and modelled `y`

---

<details>

<summary>Example output file from this callback (click to expand)</summary>

```python
[[Model]]
    Model(Gaussian  [amp * exp(-((x - x0) ** 2) / (2 * sigma**2)) + background])
[[Fit Statistics]]
    # fitting method   = leastsq
    # function evals   = 36
    # data points      = 98
    # variables        = 4
    chi-square         = 148.424352
    reduced chi-square = 1.57898247
    Akaike info crit   = 48.6805775
    Bayesian info crit = 59.0204474
    R-squared          = 0.95949614
[[Variables]]
    amp:         230.617045 +/- 10.4151289 (4.52%) (init = 287)
    sigma:       0.00969209 +/- 2.7953e-04 (2.88%) (init = 0.009036228)
    x0:          0.49905249 +/- 3.5203e-04 (0.07%) (init = 0.4999994)
    background:  0.59641742 +/- 0.13909858 (23.32%) (init = 0)
[[Correlations]] (unreported correlations are < 0.100)
    C(amp, sigma) = -0.6254
    C(sigma, x0)  = +0.1980
    C(amp, x0)    = -0.1360


x,y,y uncertainty,modelled y
0.29442974330116267,0.9362155048960608,1.1732576103594294,0.596417422655042
0.2987958123011627,1.7278474231222112,1.411659205995935,0.596417422655042
0.3013446053011628,2.2956249406851517,1.770613464899424,0.596417422655042
0.30558076430116277,3.574729064039327,2.1816903049886642,0.596417422655042
0.31062594030116286,1.0235264249142935,1.2440461004858383,0.596417422655042
...
```

</details>

---

<details>

<summary>Example configuration (click to expand)</summary>

```python
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

</details>

---

This will write data describing a fit to a file, into the path provided to the callback. If multiple fits are present simultaneously, use the `postfix` argument to append to the end of the filename to disambiguate different fits and to avoid overwriting fitting files.

If you provide a signal name for the `yerr` argument, then an extra column for `y uncertainty` will be displayed in the fitting file. Keep in mind that even if you provide `yerr` in {py:obj}`~ibex_bluesky_core.callbacks.LiveFitLogger`, you will still *also* need to provide `yerr` in {py:obj}`~ibex_bluesky_core.callbacks.LiveFit` if you want uncertainty/weight per point to influence the fit.
