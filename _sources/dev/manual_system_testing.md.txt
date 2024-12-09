# Manual system testing

Manual system tests are stored in the `manual_system_tests` directory.

Each manual system test should be run both in the PyDEV console in the GUI, and in a standalone
python window, unless the test itself says otherwise.

The tests will detail any prerequisites in it's docstrings, and will print out any checks
or expected results which you should manually verify.

## Running the tests from PyDEV in the GUI

In the PyDEV console in the GUI, type:

```
# Should print that it has loaded a named plan
g.load_script(r"c:\instrument\dev\ibex_bluesky_core\manual_system_tests\the_test.py")
# The RE object should already be defined in the PyDEV console
RE(dae_scan())
```

If the plan uses plotting, it should plot using matplotlib embedded in the IBEX GUI.

## Running from a standalone python session

- Set the following environment variables in your `cmd` session
```
set MYPVPREFIX=TE:NDWXXXX:
set "EPICS_CA_ADDR_LIST=127.255.255.255 130.246.51.255"
set "EPICS_CA_AUTO_ADDR_LIST=NO"
```
- Run the test using:
```
python c:\instrument\dev\ibex_bluesky_core\manual_system_tests\the_test.py
```

If the plan uses plotting, it should spawn a Qt matplotlib window.
