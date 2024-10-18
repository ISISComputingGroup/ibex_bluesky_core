# File writing callbacks
## Human readable files

A callback (`HumanReadableFileCallback`) exists to write all documents to a separate human-readable file which contains the specified fields. 

This callback will add units and honour precision for each field as well as add some metadata ie. the `uid` of each scan as well as the RB number, which is injected using the {doc}`/preprocessors/rbnumberpp`

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

    yield from ensure_connected(block, dae, force_reconnect=True)

    @subs_decorator(
        [
            HumanReadableFileCallback(
                Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files",
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

This will put the `block` and `dae.good_frames` data collected over the run into a `.txt` file, named after the `uid` of the scan, in `C:\instrument\var\logs\bluesky\output_files\`. The data is prepended on the first event with the names and units of each logged field, and then subsequently the data for each scan separated by a newline. All of this is separated by commas, though the metadata is not.

The file also contains some other metadata such as the bluesky version, plan type etc. - these are mostly going to be used for debugging.
