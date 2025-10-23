# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "ibex_bluesky_core"
copyright = ""
author = "ISIS Experiment Controls"
release = "0.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

nitpicky = True
nitpick_ignore_regex = [
    ("py:func", r"^(?!ibex_bluesky_core\.).*$"),
    ("py:class", r"^(?!ibex_bluesky_core\.).*$"),
    ("py:class", r"^.*\.T$"),
    ("py:obj", r"^.*\.T$"),
    ("py:class", r"^.*\.T.*_co$"),
    ("py:obj", r"^.*\.T.*_co$"),
]

myst_enable_extensions = ["dollarmath", "strikethrough", "colon_fence", "attrs_block"]
suppress_warnings = ["myst.strikethrough"]

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    # and making summary tables at the top of API docs
    "sphinx.ext.autosummary",
    # This can parse google style docstrings
    "sphinx.ext.napoleon",
    # For linking to external sphinx documentation
    "sphinx.ext.intersphinx",
    # Add links to source code in API docs
    "sphinx.ext.viewcode",
    # Mermaid diagrams
    "sphinxcontrib.mermaid",
]
mermaid_d3_zoom = True
napoleon_google_docstring = True
napoleon_numpy_docstring = False

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_context = {
    "display_github": True,  # Integrate GitHub
    "github_user": "ISISComputingGroup",  # Username
    "github_repo": "ibex_bluesky_core",  # Repo name
    "github_version": "main",  # Version
    "conf_py_path": "/doc/",  # Path in the checkout to the docs root
}

html_theme = "sphinx_rtd_theme"
html_logo = "logo.svg"
html_theme_options = {
    "logo_only": False,
    "style_nav_header_background": "#343131",
}
html_favicon = "favicon.svg"
html_static_path = ["_static"]
html_css_files = [
    "css/custom.css",
]

autoclass_content = "both"
myst_heading_anchors = 7
autodoc_preserve_defaults = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "bluesky": ("https://blueskyproject.io/bluesky/main/", None),
    "ophyd_async": ("https://blueskyproject.io/ophyd-async/v0.12.3/", None),
    "event_model": ("https://blueskyproject.io/event-model/main/", None),
    "scipp": ("https://scipp.github.io/", None),
    "scippneutron": ("https://scipp.github.io/scippneutron/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
    "matplotlib": ("https://matplotlib.org", None),
    "lmfit": ("https://lmfit.github.io/lmfit-py/", None),
    "typing_extensions": ("https://typing-extensions.readthedocs.io/en/latest/", None),
}
