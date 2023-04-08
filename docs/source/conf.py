# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

# print(os.environ["API_KEY"],"")

# sys.path.insert(0, os.path.abspath(os.path.join('../esddns/esddns_service')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
# sys.path.insert(0, os.path.abspath('/home/sqe/esdns/esddns/dns.ini'))
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
sys.path.insert(0, os.path.abspath("../.."))
# sys.path.insert(0, os.path.abspath(os.path.join('..')))

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, basedir)
print(sys.path)

project = 'ESDDNS'
copyright = '2023, Aziz Kurbanov'
author = 'Aziz Kurbanov'
release = '0.0.2'

# import esddns.esddns_service 
# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.viewcode', 
              'sphinx.ext.autodoc',
              'sphinx.ext.napoleon'
]

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']