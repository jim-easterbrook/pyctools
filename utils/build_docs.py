#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2023  Pyctools contributors
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
import shutil
import sys

from sphinx.application import Sphinx


def main(argv=None):
    root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    src_dir = os.path.join(root, 'src', 'doc')
    dst_dir = os.path.join(root, 'doc', 'html')
    doctree_dir = os.path.join(root, 'doctrees', 'html')
    shutil.rmtree(os.path.join(src_dir, 'api'), ignore_errors=True)
    app = Sphinx(src_dir, src_dir, dst_dir, doctree_dir, 'html', freshenv=True)
    app.build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
