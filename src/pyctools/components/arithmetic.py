#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-15  Jim Easterbrook  jim@jim-easterbrook.me.uk
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
frame. To set the expression, set the component's ``func`` config to a
suitable string expression. The input data should appear in your
expression as the word ``data``.

For example, to convert video levels from the range ``16..235`` to
``64..204`` you could do this::

    setlevel = Arithmetic()
    cfg = setlevel.get_config()
    cfg['func'] = '((data - pt_float(16.0)) * pt_float(140.0 / 219.0)) + pt_float(64.0)'
    setlevel.set_config(cfg)
    ...
    pipeline(..., setlevel, ...)

Note the liberal use of ``pt_float`` to coerce data to the Pyctools
default floating point type (``numpy.float32``). NumPy will otherwise
convert Python :py:class:`float` to ``numpy.float64``.

Arithmetic2 is similar, but has two inputs. For example, to subtract the
second inout from the first you could do::

    subtracter = Arithmetic2(func='data1 - data2')

"""

__all__ = ['Arithmetic', 'Arithmetic2']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigStr
from pyctools.core.base import Component, Transformer
from pyctools.core.types import pt_float, pt_complex

class Arithmetic(Transformer):
    def initialise(self):
        self.config['func'] = ConfigStr(value='data')

    def transform(self, in_frame, out_frame):
        self.update_config()
        func = self.config['func']
        data = in_frame.as_numpy()
        out_frame.data = eval(func)
        audit = out_frame.metadata.get('audit')
        audit += 'data = %s\n' % func
        out_frame.metadata.set('audit', audit)
        return True


class Arithmetic2(Component):
    inputs = ['input1', 'input2']
    with_outframe_pool = True

    def initialise(self):
        self.config['func'] = ConfigStr(value='data1 + data2')

    def process_frame(self):
        in_frame1 = self.input_buffer['input1'].get()
        in_frame2 = self.input_buffer['input2'].get()
        out_frame = self.outframe_pool['output'].get()
        self.update_config()
        func = self.config['func']
        data1 = in_frame1.as_numpy()
        data2 = in_frame2.as_numpy()
        out_frame.initialise(in_frame1)
        out_frame.data = eval(func)
        audit = 'data1 = {\n%s}\n' % in_frame1.metadata.get('audit')
        audit += 'data2 = {\n%s}\n' % in_frame2.metadata.get('audit')
        audit += 'data = %s\n' % func
        out_frame.metadata.set('audit', audit)
        self.output(out_frame)
