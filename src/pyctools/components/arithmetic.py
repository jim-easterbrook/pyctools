#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014  Jim Easterbrook  jim@jim-easterbrook.me.uk
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

"""Do simple arithmetic.

Applies a user supplied arithmetical expression to every pixel in each
frame. To set the expression, get the component's config and set its
``func`` to a suitable string expression. The input data should appear
in your expression as the word ``data``.

For example, to convert video levels from 16..235 to 64..204 you could
do this::

    setlevel = Arithmetic()
    cfg = setlevel.get_config()
    cfg['func'] = '((data - 16.0) * (140.0 / 219.0)) + 64.0'
    setlevel.set_config(cfg)
    ...
    pipeline(..., setlevel, ...)

"""

__all__ = ['Arithmetic']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigStr
from pyctools.core.base import Transformer

class Arithmetic(Transformer):
    def initialise(self):
        self.config['func'] = ConfigStr(value='data')

    def transform(self, in_frame, out_frame):
        self.update_config()
        func = self.config['func']
        in_data = in_frame.as_numpy(numpy.float32)
        out_frame.data = []
        for data in in_data:
            out_frame.data.append(eval(func))
        audit = out_frame.metadata.get('audit')
        audit += 'data = %s\n' % func
        out_frame.metadata.set('audit', audit)
        return True
