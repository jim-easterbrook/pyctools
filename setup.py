#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-24  Pyctools contributors
#
#  This file is part of Pyctools.
#
#  Pyctools is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  Pyctools is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Pyctools.  If not, see <http://www.gnu.org/licenses/>.

import numpy
import os
from setuptools import setup
from setuptools import __version__ as setuptools_version
import sys

# import Cython after distutils/setuptools
from Cython.Build import cythonize

version = '0.6.0'

# import common Pyctools setup
with open(os.path.join('src', 'pyctools', 'setup.py')) as f:
    exec(f.read())

# find packages
packages = find_packages()

# Make sure each package is a "pkgutil-style namespace package"
# See https://packaging.python.org/guides/packaging-namespace-packages/
write_init_files(packages)

console_scripts = []
for name in os.listdir(os.path.join('src', 'pyctools', 'tools')):
    base, ext = os.path.splitext(name)
    if name.startswith('_') or ext != '.py':
        continue
    console_scripts.append(
        'pyctools-{name} = pyctools.tools.{name}:main'.format(name=base))

ext_modules = cythonize(find_ext_modules(), compiler_directives={
    'language_level' : sys.version_info[0]})

setup_kwds = {
    'ext_modules': ext_modules,
    'packages': packages,
    'package_dir': {'' : 'src'},
    'entry_points': {
        'console_scripts' : console_scripts,
        },
    }

if tuple(map(int, setuptools_version.split('.'))) < (61, 0):
    # get metadata from pyproject.toml
    import toml
    metadata = toml.load('pyproject.toml')

    with open(metadata['project']['readme']) as ldf:
        long_description = ldf.read()

    setup_kwds.update(
        name = metadata['project']['name'],
        version = metadata['project']['version'],
        description = metadata['project']['description'],
        long_description = long_description,
        author = metadata['project']['authors'][0]['name'],
        author_email = metadata['project']['authors'][0]['email'],
        url = metadata['project']['urls']['homepage'],
        classifiers = metadata['project']['classifiers'],
        platforms = metadata['tool']['setuptools']['platforms'],
        license = metadata['project']['license']['text'],
        zip_safe = metadata['tool']['setuptools']['zip-safe'],
        )

setup(**setup_kwds)
