# File writing callbacks

{#hr_file_cb}
## Human readable files

{py:obj}`~ibex_bluesky_core.callbacks.HumanReadableFileCallback` can be configured to write all documents to a human-readable file which contains the specified fields.

This callback will add units and honour precision for each field as well as add some metadata, for example the RB number, which is injected using the {doc}`/dev/rbnumberpp`.

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

    yield from ensure_connected(block, dae, force_reconnect=True)

    @subs_decorator(
        [
            HumanReadableFileCallback(
                [
                    block.name,
                    dae.good_frames.name,
                ],
            ),
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

This will put the `block` and `dae.good_frames` data collected over the run into a `.txt` file, named after the `uid` 
of the scan, in `\\isis\inst$\ndx<inst>\user\bluesky_scans\<rbnumber>`. 

Optional parameters, not shown above, include:
- `output_dir` parameter is optional; if not provided, the file will by default be placed in 
`\\isis\inst$\ndx<inst>\user\bluesky_scans\<rbnumber>`. 
- `postfix` an optional suffix to append to the end of the file name, to disambiguate scans. Default is no suffix.

The data is prepended on the first event with the names and units of each logged field, and then subsequently the data 
for each scan separated by a newline. The data is separated by commas, though the metadata is not.

The file also contains metadata such as the bluesky version, plan type, and RB number.

## Fit outputs

See {ref}`livefit_logger`

## Plot PNGs

See {ref}`plot_png_saver`

{#event_doc_cb}
## Bluesky Event documents

```{note}
This callback is added automatically and is not intended to be user-facing - it is primarily for developer diagnostics.
```

The {py:obj}`~ibex_bluesky_core.callbacks.DocLoggingCallback` is a callback that the BlueSky RunEngine subscribes to unconditionally during {py:obj}`~ibex_bluesky_core.run_engine.get_run_engine`. It logs all documents it receives into files grouped by unique scan identifier. These logs are stored under `C:/instrument/var/logs/bluesky/raw_documents`; older logs are moved to long-term storage by a log rotation script.

Each document is stored in a JSON format so can be both machine and human-readable. The format is line-delimited JSON, `{"type": name, "document": document}` whereby `name` is the type of the document, e.g start, stop, event, descriptor and the `document` is the {external+bluesky:doc}`document from bluesky in JSON format <documents>`.
