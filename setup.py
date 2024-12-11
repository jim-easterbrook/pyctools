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
from setuptools import setup


# import common Pyctools setup
with open(os.path.join('src', 'pyctools', 'setup.py')) as f:
    exec(f.read())


setup(**get_setup_parameters())
