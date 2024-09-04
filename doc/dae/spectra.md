# DAE Spectra

Raw spectra are provided by the `DaeSpectra` class. Not all spectra are automatically available
on the base DAE object - user classes will define the specific set of spectra which they are
interested in.

A `DaeSpectrum` object provides 3 arrays:
- `tof` (x-axis): time of flight.
- `counts` (y-axis): number of counts
  - Suitable for summing counts
  - Will give a discontinuous plot if plotted directly and bin widths are non-uniform.
- `counts_per_time` (y-axis): number of counts normalized by bin width
  - Not suitable for summing counts directly
  - Gives a continuous plot when plotted against x directly.

The `Dae` base class does not provide any spectra by default. User-level classes should specify 
the set of spectra which they are interested in.
