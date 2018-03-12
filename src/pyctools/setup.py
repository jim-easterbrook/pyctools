#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-18  Pyctools contributors
#
#  This program is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see
#  <http://www.gnu.org/licenses/>.

import os

import numpy
from setuptools import Extension

def find_ext_modules():
    ext_modules = []
    for root, dirs, files in os.walk(os.path.join('src', 'pyctools')):
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
                ))
    return ext_modules

def find_packages():
    """Walk source directory tree and convert each sub directory to a
    package name.

    """
    packages = ['pyctools']
    for root, dirs, files in os.walk(os.path.join('src', 'pyctools')):
        package = '.'.join(root.split(os.sep)[1:])
        for name in dirs:
            packages.append(package + '.' + name)
    return packages

def write_init_files(packages):
    """Make sure package hierarchy is a "pkgutil-style namespace
    package". For more detail see
    https://packaging.python.org/guides/packaging-namespace-packages/
    
    """
    init_text = """__path__ = __import__('pkgutil').extend_path(__path__, __name__)

try:
    from .__doc__ import __doc__
except ImportError:
    pass
"""
    for package in packages:
        path = os.path.join('src', package.replace('.', os.sep), '__init__.py')
        if os.path.exists(path):
            with open(path) as f:
                old_text = f.read()
        else:
            old_text = ''
        if old_text != init_text:
            with open(path, 'w') as f:
                f.write(init_text)
