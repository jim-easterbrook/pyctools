#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2024  Pyctools contributors
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

import ast
import os
import sys

# requires GitPython - 'pip install --user gitpython'
import git
import toml


def main(argv=None):
    # get root dir
    root = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
    # get pyctools version
    metadata = toml.load('pyproject.toml')
    version = metadata['project']['version']
    message = 'v' + version + '\n\n'
    with open(os.path.join(root, 'CHANGELOG.txt')) as cl:
        while not cl.readline().startswith('Changes'):
            pass
        while True:
            line = cl.readline().strip()
            if not line:
                break
            message += line + '\n'
    repo = git.Repo()
    tag = repo.create_tag('v' + version, message=message)
    remote = repo.remotes.origin
    remote.push(tags=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
