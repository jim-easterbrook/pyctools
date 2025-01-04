# Pyctools - a picture processing algorithm development kit.
# http://github.com/jim-easterbrook/pyctools
# Copyright (C) 2014-25  Pyctools contributors
#
# This file is part of Pyctools.
#
# Pyctools is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Pyctools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pyctools.  If not, see <http://www.gnu.org/licenses/>.

import os
import site
import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))
site.addsitedir(os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.autosummary',
              'sphinx.ext.viewcode', 'sphinx.ext.intersphinx',
              'sphinx_rtd_theme']

autoclass_content = 'class'
autodoc_member_order = 'bysource'
autodoc_default_options = {
    'members': True,
    'show-inheritance': True,
    }
##autosummary_generate = False

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://docs.scipy.org/doc/numpy/', None),
    'PIL': ('https://pillow.readthedocs.io/en/latest/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/reference/', None),
    }

keep_warnings = True

# Add any paths that contain templates here, relative to this directory.
#templates_path = ['templates']

rst_epilog = """
----

Comments or questions? Please email jim@jim-easterbrook.me.uk.
"""

# The suffix of source filenames.
source_suffix = {'.rst': 'restructuredtext'}

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Pyctools'
copyright = u'2014-25, Pyctools contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
#version = 
# The full version, including alpha/beta/rc tags.
#release =
import toml
version = toml.load('../../pyproject.toml')['project']['version']
release = version
version = '.'.join(version.split('.')[0:2])

# search installed package for modules to document
try:
    import pyctools
except ImportError:
    print("Pyctools is not installed")
    sys.exit(1)
modules = []
# pkgutil.walk_packages doesn't work with namespace packages, so we do
# a simple file search instead
for path in pyctools.__path__:
    depth = len(path.split(os.path.sep)) - 1
    for root, dirs, files in os.walk(path):
        parts = root.split(os.path.sep)
        if parts[-1] == '__pycache__':
            continue
        parts = parts[depth:]
        if len(parts) > 1:
            module = {
                'name'  : '.'.join(parts),
                'ispkg' : True,
                'depth' : len(parts),
                'intoc' : False,
                }
            if module not in modules:
                modules.append(module)
        for name in files:
            base, ext = os.path.splitext(name)
            if base == '__init__' or ext != '.py':
                continue
            module = {
                'name'  : '.'.join(parts + [base]),
                'ispkg' : False,
                'depth' : len(parts) + 1,
                'intoc' : False,
                }
            if module not in modules:
                modules.append(module)
modules.sort(key=lambda x: x['name'])

def update_file(path, new_contents):
    if os.path.exists(path):
        old_contents = open(path).read()
        if old_contents == new_contents:
            return
    with open(path, 'w') as f:
        f.write(new_contents)

def submodules(parent):
    for module in modules:
        if (module['depth'] == parent['depth'] + 1 and
            module['name'].startswith(parent['name'])):
            yield module

# write package indexes
for package in [x for x in modules if x['ispkg']]:
    dir_name = os.path.join('api', package['name'].split('.')[1])
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)
    # visible index, include classes, exclude undocumented
    title = '.'.join(package['name'].split('.')[1:])
    idx_str = title + '\n' + ('=' * len(title)) + '\n\n'
    idx_str += '.. automodule:: ' + package['name'] + '\n\n'
    idx_str += ('.. autosummary::\n' +
                '   :nosignatures:\n\n')
    for module in submodules(package):
        name = module['name'].replace(package['name'] + '.', '')
        if module['ispkg']:
            idx_str += '   ' + name + '\n'
            module['intoc'] = True
            continue
        # import module
        try:
            mod = __import__(module['name'], globals(), locals(), ['*'])
        except ImportError as ex:
            print(str(ex))
            continue
        module['mod'] = mod
        if getattr(mod, '__doc__'):
            idx_str += '   ' + name + '\n'
            module['intoc'] = True
        for member in [x for x in getattr(mod, '__all__', [])
                       if getattr(getattr(mod, x), '__doc__')]:
            idx_str += '   ' + name + '.' + member + '\n'
            module['intoc'] = True
    idx_str += '\n'
    # toctree entries, child packages and modules only
    idx_str += ('.. toctree::\n' +
                '   :hidden:\n\n')
    for module in submodules(package):
        if module['intoc']:
            idx_str += '   ' + module['name'] + '\n'
    idx_str += '\n'
    update_file(os.path.join(dir_name, package['name'] + '.rst'), idx_str)

# write module stubs
for module in [x for x in modules if x['intoc'] and not x['ispkg']]:
    dir_name = os.path.join('api', module['name'].split('.')[1])
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)
    # module stub
    title = '.'.join(module['name'].split('.')[1:])
    mod_str = title + '\n' + ('=' * len(title)) + '\n\n'
    mod_all = getattr(module['mod'], '__all__', [])
    if len(mod_all) > 1:
        mod_str += '.. autosummary::\n'
        mod_str += '   :nosignatures:\n\n'
        for member in mod_all:
            mod_str += '   ' + module['name'] + '.' + member + '\n'
        mod_str += '\n'
    mod_str += '.. automodule:: ' + module['name'] + '\n'
    if not module['name'].startswith('pyctools.core'):
        mod_str += '   :exclude-members: initialise, process_frame, transform,\n'
        mod_str += '      on_connect, on_set_config, on_start, on_stop\n'
    mod_str += '\n'
    update_file(os.path.join(dir_name, module['name'] + '.rst'), mod_str)

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True
add_function_parentheses = False

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True
add_module_names = False

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_css_files = ['theme_overrides.css']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Pyctoolsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Pyctools.tex', u'Pyctools Documentation',
   u'Jim Easterbrook', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'pyctools', u'Pyctools Documentation',
     [u'Jim Easterbrook'], 1)
]
