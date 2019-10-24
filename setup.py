#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-19  Pyctools contributors
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
from distutils.command.upload import upload
import numpy
import os
from setuptools import setup, Extension
import sys

version = '0.5.0'

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

ext_modules = find_ext_modules()

# Use Cython version of 'build_ext' command
cmdclass = {'build_ext': build_ext}
command_options = {}

# if sphinx is installed, add command to build documentation
try:
    from sphinx.setup_command import BuildDoc
except ImportError:
    pass
else:
    cmdclass['build_sphinx'] = BuildDoc
    command_options['build_sphinx'] = {
        'all_files'  : ('setup.py', '1'),
        'source_dir' : ('setup.py', 'src/doc'),
        'build_dir'  : ('setup.py', 'doc'),
        'builder'    : ('setup.py', 'html'),
        }

# set options for uploading documentation to PyPI
command_options['upload_docs'] = {
    'upload_dir' : ('setup.py', 'doc/html'),
    }

# modify upload command to add appropriate tag
# requires GitPython - 'sudo pip install gitpython --pre'
try:
    import git
except ImportError:
    pass
else:
    class upload_and_tag(upload):
        def run(self):
            tag_path = 'v%s' % version
            message = '%s\n\n' % tag_path
            with open('CHANGELOG.txt') as f:
                while not f.readline().startswith('Changes'):
                    pass
                while True:
                    line = f.readline().strip()
                    if not line:
                        break
                    message += line + '\n'
            repo = git.Repo()
            tag = repo.create_tag(tag_path, message=message)
            remote = repo.remotes.origin
            remote.push(tags=True)
            return upload.run(self)
    cmdclass['upload'] = upload_and_tag

with open('README.rst') as f:
    long_description = f.read()
url = 'https://github.com/jim-easterbrook/pyctools'

setup(name = 'pyctools.core',
      version = version,
      author = 'Jim Easterbrook',
      author_email = 'jim@jim-easterbrook.me.uk',
      url = url,
      description = 'Picture processing algorithm development kit',
      long_description = long_description,
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
      ext_modules = ext_modules,
      package_dir = {'' : 'src'},
      entry_points = {
          'console_scripts' : console_scripts,
          },
      install_requires = ['cython', 'numpy', 'setuptools'],
      cmdclass = cmdclass,
      command_options = command_options,
      zip_safe = False,
      )
