# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = 'csql'
copyright = '2021, Jarrad Whitaker'
author = 'Jarrad Whitaker'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'myst_parser',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosummary',
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.doctest',
    'sphinx_external_toc',
    'extensions.csql_docs'
]
external_toc_path = "_toc.yml"  # optional, default: _toc.yml
# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- autodoc stuff -----
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
#autodoc_class_signature = 'separated'
autodoc_default_options = {
    'members': True,
    'undoc-members': True
}
autodoc_type_aliases = {
    'ParameterValue': 'csql.ParameterValue',
    'Key': 'csql.persist.Key'
}

# -- myst stuff
myst_enable_extensions = ['linkify']
tab_width = 4

# -- doctest stuff
doctest_test_doctest_blocks = 'yes'

doctest_global_setup = '''
import csql
import csql.dialect
import csql.contrib.persist
from csql import Q, Parameters
from datetime import date, datetime


import sqlite3
def my_connection():
   c = sqlite3.connect(':memory:')
   c.execute('create view slow_view as select 123 as val')
   return c

class DummyCursor:
    def execute(self, s: str, params = None):
        return None

    def __enter__(self, *args, **kwargs): return self
    def __exit__(self, *args, **kwargs): return self.close()
    def close(self): pass

    @property
    def description(self):
        return ()

    def fetchall(self):
        return [[]]

class DummyDatabase:
    def cursor(self):
        return DummyCursor()

def some_connection():
    return DummyDatabase()

'''

import doctest

IGNORE_RESULT = doctest.register_optionflag('IGNORE_RESULT')

from pprint import pprint
pprint(doctest.OPTIONFLAGS_BY_NAME)

OutputChecker = doctest.OutputChecker
class CustomOutputChecker(OutputChecker):
    def check_output(self, want, got, optionflags):
        if IGNORE_RESULT & optionflags:
            return True
        return OutputChecker.check_output(self, want, got, optionflags)

doctest.OutputChecker = CustomOutputChecker



# -- sphinx-autodoc-typehints stuff
#set_type_checking_flag = True

# -- intersphinx
intersphinx_mapping = {
    'pandas': ('https://pandas.pydata.org/docs/', None)
}

autosummary_generate = False
autosummary_imported_members = True
autosummary_ignore_module_all = False


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'
html_theme_options = {

}
html_css_files = [
    'css/custom.css',
]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']