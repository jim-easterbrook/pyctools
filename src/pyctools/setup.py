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

import os
import sys

import numpy
from setuptools import Extension
from setuptools import __version__ as setuptools_version
import toml

# import Cython after setuptools
from Cython.Build import cythonize

# get metadata from pyproject.toml
metadata = toml.load('pyproject.toml')
find_kwds = metadata['tool']['setuptools']['packages']['find']
find_kwds['where'] = find_kwds['where'][0]


def find_console_scripts():
    path = os.path.join(find_kwds['where'], 'pyctools', 'tools')
    if not os.path.exists(path):
        return []
    console_scripts = []
    for name in os.listdir(path):
        base, ext = os.path.splitext(name)
        if name.startswith('_') or ext != '.py':
            continue
        console_scripts.append(
            'pyctools-{name} = pyctools.tools.{name}:main'.format(name=base))
    return console_scripts


def find_ext_modules():
    ext_modules = []
    for root, dirs, files in os.walk(os.path.join(
            find_kwds['where'], 'pyctools')):
        for name in files:
            base, ext = os.path.splitext(name)
            if ext != '.pyx':
                continue
            ext_modules.append(Extension(
                '.'.join(root.split(os.sep)[1:] + [base]),
                [os.path.join(root, name)],
                include_dirs = [numpy.get_include()],
                extra_compile_args = [
                    '-fopenmp', '-Wno-maybe-uninitialized', '-Wno-unused-function'],
                extra_link_args = ['-fopenmp'],
                define_macros=[
                    ('NPY_NO_DEPRECATED_API', 'NPY_1_7_API_VERSION')],
                ))
    return cythonize(ext_modules, compiler_directives={
        'language_level' : sys.version_info[0]})

def get_setup_parameters():
    setup_kwds = {
        'ext_modules': find_ext_modules(),
        'entry_points': {
            'console_scripts' : find_console_scripts(),
            },
        }
    if tuple(map(int, setuptools_version.split('.'))) < (61, 0):
        # use setuptools' find_namespace_packages directly
        from setuptools import find_namespace_packages
        setup_kwds['packages'] = find_namespace_packages(**find_kwds)
        setup_kwds['package_dir'] = {'': find_kwds['where']}
        # copy metadata from pyproject.toml
        if os.path.exists(metadata['project']['readme']):
            with open(metadata['project']['readme']) as ldf:
                setup_kwds['long_description'] = ldf.read()
        setup_kwds.update(
            name = metadata['project']['name'],
            version = metadata['project']['version'],
            description = metadata['project']['description'],
            author = metadata['project']['authors'][0]['name'],
            author_email = metadata['project']['authors'][0]['email'],
            url = metadata['project']['urls']['homepage'],
            classifiers = metadata['project']['classifiers'],
            platforms = metadata['tool']['setuptools']['platforms'],
            license = metadata['project']['license']['text'],
            zip_safe = metadata['tool']['setuptools']['zip-safe'],
            )
    return setup_kwds
