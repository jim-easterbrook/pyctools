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

__all__ = ['Modulate']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.base import Transformer
from pyctools.core.types import pt_float

class Modulate(Transformer):
    """Modulate or sample an image.

    Multiplies each pixel value by a modulating value that can vary
    horizontally, vertically and temporally. The modulating function is
    supplied in a small "cell" whose dimensions should be the repeat
    period of the function in each direction.

    The ``cell`` input method is used to update the modulating function.
    No processing happens until a cell is received, and new cells can be
    applied while the component is running.

    The cell is supplied in a :py:class:`~pyctools.core.frame.Frame`
    object sent to the ``cell`` input. Unlike most other
    :py:class:`~pyctools.core.frame.Frame` objects the data must have 4
    dimensions. If the first dimension is greater than unity then the
    modulation function can have a temporal variation.

    If the cell data's 4th dimension is unity then the same modulation
    is applied to each component of the input. Alternatively the cell
    data's 4th dimension should match the input's, allowing a different
    modulation to be applied to each colour.

    For example, a cell to simulate a `Bayer filter
    <http://en.wikipedia.org/wiki/Bayer_filter>`_ could look like this::

        cell = Frame()
        cell.data = numpy.array([[[[0, 0, 1], [0, 1, 0]],
                                  [[0, 1, 0], [1, 0, 0]]]], dtype=numpy.float32)
        cell.type = 'cell'
        audit = cell.metadata.get('audit')
        audit += 'data = Bayer filter modulation cell\\n'
        cell.metadata.set('audit', audit)

    """

    inputs = ['input', 'cell']  #:

    def initialise(self):
        self.cell_frame = None

    def get_cell(self, in_data):
        cell_frame = self.input_buffer['cell'].peek()
        if (cell_frame == self.cell_frame and
                self.cell_data.shape[1:] == in_data.shape):
            return True
        cell_data = cell_frame.as_numpy()
        if cell_data.ndim != 4:
            self.logger.error('Cell input must be 4 dimensional')
            self.input_buffer['cell'].get()
            return False
        if cell_data.shape[3] not in (1, in_data.shape[2]):
            self.logger.warning('Mismatch between %d cells and %d components',
                                cell_data.shape[3], in_data.shape[2])
        # repeat cell to frame dimensions
        if in_data.dtype == cell_data.dtype:
            dtype = cell_data.dtype
        else:
            dtype = pt_float
        repeated_cell = numpy.empty((cell_data.shape[0],) + in_data.shape, dtype)
        d_k, d_j, d_i, d_c = cell_data.shape
        for k in range(d_k):
            for j in range(d_j):
                for i in range(d_i):
                    for c in range(d_c):
                        repeated_cell[k, j::d_j, i::d_i, c::d_c] = cell_data[k, j, i, c]
        self.cell_frame = cell_frame
        self.cell_data = repeated_cell
        return True

    def transform(self, in_frame, out_frame):
        in_data = in_frame.as_numpy()
        if not self.get_cell(in_data):
            return False
        k = in_frame.frame_no % self.cell_data.shape[0]
        out_frame.data = in_data * self.cell_data[k]
        audit = out_frame.metadata.get('audit')
        audit += 'data = Modulate(data)\n'
        audit += '    cell: {\n'
        for line in self.cell_frame.metadata.get('audit').splitlines():
            audit += '        ' + line + '\n'
        audit += '        }\n'
        out_frame.metadata.set('audit', audit)
        return True
