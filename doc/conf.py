# -*- coding: utf-8 -*-
#
# asterism documentation build configuration file, created by
# sphinx-quickstart on Thu Apr 21 10:33:01 2016.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os
import json
import mock
#import jetset
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0,os.path.abspath('../'))
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'


autodoc_mock_imports=[]
autodoc_mock_imports = ["jetkernel"]
autodoc_mock_imports.append('_jetkernel')
autodoc_mock_imports.append('gammapy')
autodoc_mock_imports.append('sherpa')

for mod_name in autodoc_mock_imports:
    sys.modules[mod_name] = mock.Mock()


import sphinx_bootstrap_theme
if on_rtd==False:  # only import and set the  if we're building docs locally
    theme = 'sphinx_book_theme'
else:
    theme = 'sphinx_book_theme'


extensions = [
    #'autoapi.extension'
    'sphinx.ext.autodoc',
    'sphinx_automodapi.automodapi',
    'sphinx_automodapi.smart_resolver',
    'sphinx_gallery.load_style',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'sphinx.ext.autosummary',
    'sphinx.ext.graphviz',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.napoleon',
    'sphinx.ext.inheritance_diagram',
    'sphinx.ext.autosummary',
    'nbsphinx',
#   'sphinxcontrib.bibtex',
    'sphinx.ext.mathjax',
]

#bibtex_bibfiles = ['refs.bib']
#bibtex_bibfiles = ['references.bib']
exclude_patterns = ['_build', 
                    '**.ipynb_checkpoints',
                    '../jetkernel/*',
                    '../jetset/jetkernel/*',
                    'documentation_notebooks',
                    'example_notebooks',
                    'slides']

#autoapi_dirs = ['../jetset']

#templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'
with open('../jetset/pkg_info.json') as fp:
    _info = json.load(fp)
__version__ = _info['version']
#import jetset
#__version__ = jetset.__version__

# General information about the project.
# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
project = u'jetset'
copyright = u'2019, andrea tramacere'





#add_module_names = False
#pygments_style = 'sphinx'





#html_static_path = ['_static']
#html_logo = "_static/logo_small_color_transparent.png"



if theme=='sphinx_book_theme':
    html_theme = "sphinx_book_theme"
    html_static_path = ["_static/css/sphinx_book_theme"]
    html_css_files = ["custom.css"]
    html_context = {
        "default_mode": "light"
    }
    #html_sidebars = {
    #"**": ["sbt-sidebar-nav.html"]
    #}
    pygments_style = "friendly"
    pygments_dark_style = "nord"

    html_theme_options = {
        "icon_links": [
        {
            # Label for this link
            "name": "GitHub",
            # URL where the link will redirect
            "url": "https://github.com/andreatramacere/jetset",  # required
            # Icon class (if "type": "fontawesome"), or path to local image (if "type": "local")
            "icon": "fa-brands fa-square-github",
            # The type of image to be used (see below for details)
            "type": "fontawesome",
            }        
         ],
        #"show_version_warning_banner": True,
        #"collapse_navigation": True,
        #"navbar_start": ["navbar-logo"],
        #"navbar_center": ["navbar-nav"],
        #"navbar_end": ["navbar-icon-links"],
        #"navbar_persistent": ["search-button"],
        "logo": {
            # In a left-to-right context, screen readers will read the alt text
            # first, then the text, so this example will be read as "P-G-G-P-Y
            # (short pause) Home A pretty good geometry package"
            "alt_text": "JetSeT ",
            #text": "documentation",
            "image_light": "_static/logo_book_sphinx.svg",
            "image_dark": "_static/logo_book_sphinx.svg",
        },
        "show_toc_level": 3,

    }

 

htmlhelp_basename = 'jetsetdoc'


# -- Options for LaTeX output ---------------------------------------------
latex_engine = 'pdflatex'
latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'jetset.tex', u'jetset Documentation',
   u'andrea tramacere', 'manual'),
]


man_pages = [
    ('index', 'jetset', u'jetset Documentation',
     [u'andrea tramacere'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'jetset', u'jetset Documentation',
   u'andrea tramacere', 'jetset', 'One line description of project.',
   'Miscellaneous'),
]



# Bibliographic Dublin Core info.
epub_title = u'jetset'
epub_author = u'andrea tramacere'
epub_publisher = u'andrea tramacere'
epub_copyright = u'2016, andrea tramacere'


epub_exclude_files = ['search.html']


