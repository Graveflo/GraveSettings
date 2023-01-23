# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import grave_settings

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'grave_settings'
copyright = '2023, Ryan McConnell'
author = 'Ryan McConnell'
release = grave_settings.VERSION

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autodoc",
              "sphinx.ext.viewcode",
              "sphinx.ext.intersphinx",
              'sphinx_copybutton',
              #'sphinx.ext.autosummary',
              #'sphinx.ext.napoleon'
              ]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'observer_hooks': ('https://ilikescaviar.github.io/ObserverHooks/', None)
}

templates_path = ['_templates']
exclude_patterns = []
autosummary_generate = True
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
autodoc_typehints_description_target = 'all'
autodoc_default_options = {
    "members": True,
    "special-members": False,
    "private-members": False,
    "inherited-members": False,
    "undoc-members": True
}
# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']

html_context = {
    "default_mode": "dark"
}
