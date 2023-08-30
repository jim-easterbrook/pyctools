#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-23  Pyctools contributors
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

from distutils.command.upload import upload
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

# Add / modify setuptools commands
cmdclass = {}

# modify upload command to add appropriate tag
# requires GitPython - 'sudo pip install gitpython'
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


setup_kwds = {
    'ext_modules': ext_modules,
    'packages': packages,
    'package_dir': {'' : 'src'},
    'entry_points': {
        'console_scripts' : console_scripts,
        },
    'cmdclass': cmdclass,
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
