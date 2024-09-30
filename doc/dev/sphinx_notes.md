# Notes on Sphinx and addons

This repository uses sphinx with some addons to build documentation and then deploy it to Github pages. The deployment only occurs when changes are made to main, and changes are published to the `gh-pages` branch which are then served via the page. 

We use the [MyST](https://myst-parser.readthedocs.io/en/latest/index.html) parser which lets us use a mixture of markdown and reStructuredText in documentation - though the latter is preferred by sphinx. 

## Using MyST admonitions
To use [MyST admonitions](https://myst-parser.readthedocs.io/en/latest/syntax/admonitions.html), you need to use backticks instead of triple colons, ie. 

\`\`\`{tip}\
Let's give readers a helpful hint!\
\`\`\`

becomes

```{tip}
Let's give readers a helpful hint!
```

## Code blocks in docstrings
To add code blocks within the docstrings of classes or functions, use the `::` marker along with a newline then the indented code. For example:

```
 """...

    Basic usage:

    - Get the IBEX run engine::

        RE = get_run_engine()

    - Run a plan::

        from bluesky.plans import count  # Or any other plan
        det = ...  # A "detector" object, for example a Block or Dae device.
        RE(count([det]))

    - Control the state of the run engine::

        RE.abort(reason="...")  # Stop a plan, do cleanup, and mark as failed (e.g. bad data).
        RE.stop()  # Stop a plan, do cleanup, mark as success"(e.g. scan has moved past peak).
        RE.halt()  # Stop a plan, don't do any cleanup, just abort with no further action.
        RE.resume()  # Resume running a previously-paused plan.

    - Subscribe to data emitted by this run engine::
    
        RE.subscribe(lambda name, document: ...)
    ...
    """
```
