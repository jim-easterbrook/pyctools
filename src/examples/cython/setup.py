#!/usr/bin/env python

## Replace the following with your project details and licence.
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-16  Pyctools contributors
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

from Cython.Distutils import build_ext
import numpy
import os
from setuptools import setup, Extension

version = '0.0.0'

# find packages
packages = ['pyctools']
for root, dirs, files in os.walk('src/pyctools'):
    package = '.'.join(root.split(os.sep)[1:])
    for name in dirs:
        packages.append(package + '.' + name)

# make sure each package is a "namespace package"
init_text = """__import__('pkg_resources').declare_namespace(__name__)

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

# find Cython extensions
ext_modules = []
for root, dirs, files in os.walk('src/pyctools'):
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

# Use Cython version of 'build_ext' command
cmdclass = {'build_ext': build_ext}

## Edit 'name', 'author', 'author_email', 'url' and 'description'. You
## may want to add a 'long_description' field and change the
## 'classifiers' later
setup(name = 'pyctools.example',
      version = version,
      author = 'Jim Easterbrook',
      author_email = 'jim@jim-easterbrook.me.uk',
      url = 'https://github.com/jim-easterbrook/pyctools',
      description = 'Example Pyctools component',
      classifiers = [
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Topic :: Multimedia :: Graphics',
          'Topic :: Multimedia :: Video',
          'Topic :: Scientific/Engineering :: Image Recognition',
          'Topic :: Scientific/Engineering :: Visualization',
          ],
      license = 'GNU GPL',
      platforms = ['POSIX', 'MacOS'],
      packages = packages,
      namespace_packages = packages,
      ext_modules = ext_modules,
      package_dir = {'' : 'src'},
      install_requires = ['pyctools.core'],
      cmdclass = cmdclass,
      zip_safe = False,
      )
