# Replaying documents

All {external+bluesky:doc}`callbacks <callbacks>` in bluesky operate on a data structure called a {external+bluesky:doc}`document <documents>`. These documents represent the metadata and data emitted by a bluesky scan.

```{tip}
The schema of these documents is defined formally by the bluesky {external+event_model:doc}`event model <explanations/data-model>`. However, the implementation details of these documents are not important for simply replaying them.

If instead you wish to write a tool to consume bluesky documents _without_ using the callbacks provided in this library or in bluesky, please {external+ibex_user_manual:ref}`get in touch with experiment controls <report_a_problem>` for advice.
```

All bluesky {external+bluesky:doc}`callbacks <callbacks>` consume {external+bluesky:doc}`documents <documents>` as their source of data or metadata. This means that historic documents can be replayed into one or more callbacks. This facilitates:
- Replaying documents into plotting callbacks to 'replot' a scan
- Replaying documents into (potentially different) fitting callbacks, to experiment with different fitting routines
- Developing entirely new callbacks using data from historic scans

## Document storage and replay from file

The IBEX {py:obj}`RunEngine <ibex_bluesky_core.run_engine.get_run_engine>` instance is configured to automatically save the raw documents from any scan - these are saved into
```
c:\Instrument\var\logs\bluesky\raw_documents
```
They are subsequently moved to a backups area after 10 days; if you need access to old scans, please contact experiment controls for the exact path you will need.

These files are organised as line-delimited JSON dictionaries. The filename is the unique identifier of the scan.

Documents can be loaded from their save files and replayed into arbitrary callbacks - which can be a completely different set of callbacks than were used during the scan. The following example shows replay into a {py:obj}`LivePlot <ibex_bluesky_core.callbacks.LivePlot>` callback to regenerate a matplotlib plot, as well as re-running a Gaussian fit using the {py:obj}`LiveFit <ibex_bluesky_core.callbacks.LiveFit>` callback and displaying that on the plot using {external+bluesky:py:obj}`LiveFitPlot <bluesky.callbacks.mpl_plotting.LiveFitPlot>`.

```python
import json
import matplotlib.pyplot as plt
from ibex_bluesky_core.callbacks import LivePlot, LiveFit
from ibex_bluesky_core.fitting import Gaussian
from bluesky.callbacks import LiveFitPlot


def replot_scan(path_to_save_file: str, y_name: str, x_name: str):
    # Prepare a set of matplotlib axes to plot onto
    plt.close("all")
    plt.show()
    _, ax = plt.subplots()

    # Example callbacks for plotting and fitting - the exact callbacks
    # to use when replotting a scan can be chosen freely.
    live_plot = LivePlot(y_name, x_name, marker="x", linestyle="none", ax=ax)
    live_fit = LiveFit(Gaussian.fit(), y=y_name, x=x_name)
    live_fit_plot = LiveFitPlot(livefit=live_fit, ax=ax, num_points=10000)

    # Open the relevant save-file
    with open(path_to_save_file) as f:
        for line in f:
            # Load the JSON representation of this document.
            document = json.loads(line)
            # Pass the document to arbitrary callbacks.
            live_plot(document["type"], document["document"])
            live_fit_plot(document["type"], document["document"])
```
