from ibex_bluesky_core.callbacks.fitting import LiveFit

# Test ideas
# For each fit, test the model func:
#   Given a set of params and input should give the same output always
# Test the guess func:
#   Given x,y sets of data should always give the same closely correct output params
#   Could also do a test with params with random noise, check that it can fit using r^2
# Some tests for custom fit models, custom guess + std model then vice versa 