import matplotlib.pyplot as plt
from ibex_bluesky_core.callbacks import LiveFit, LivePlot
from ibex_bluesky_core.fitting import Gaussian
from bluesky.callbacks import LiveFitPlot
from ibex_bluesky_core.run_engine import get_run_engine
from ibex_bluesky_core.plans.reflectometry import refl_scan

RE = get_run_engine()

# Create a new figure to plot onto.
plt.figure()
# Make a new set of axes on that figure
ax = plt.gca() 
# ax is shared by fit_callback and plot_callback 

plot_callback = LivePlot(y="y_signal", x="x_signal", ax=ax, yerr="yerr_signal")
fit_callback = LiveFit(Gaussian.fit(), y="y_signal", x="x_signal", yerr="yerr_signal", update_every=0.5)
# Using the yerr parameter allows you to use error bars.
# update_every = in seconds, how often to recompute the fit. If `None`, do not compute until the end. Default is 1.
fit_plot_callback = LiveFitPlot(fit_callback, ax=ax, color="r")


def my_plan():
    ...  # Some stuff before scan
    icc = (yield from refl_scan("S1VG", 1, 10, 21, model=Gaussian().fit(), frames=500, det=100, mon=3, pixel_range=6, periods=True, save_run=False))
    ...  # Some stuff after scan


RE(my_plan(), LivePlot=plot_callback, LiveFit=fit_callback, LiveFitPlot=fit_plot_callback)
plt.show()