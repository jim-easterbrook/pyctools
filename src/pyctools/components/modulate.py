#!/usr/bin/env python
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

__all__ = ['Modulate']
__docformat__ = 'restructuredtext en'

from pyctools.core.base import Transformer

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

    inputs = ['input', 'cell']

    def initialise(self):
        self.cell_frame = None

    def get_cell(self, in_data):
        cell_frame = self.input_buffer['cell'].peek()
        if cell_frame == self.cell_frame:
            return True
        self.cell_data = cell_frame.as_numpy()
        if self.cell_data.ndim != 4:
            self.logger.error('Cell input must be 4 dimensional')
            self.input_buffer['cell'].get()
            return False
        if self.cell_data.shape[3] not in (1, in_data.shape[2]):
            self.logger.warning('Mismatch between %d cells and %d components',
                                self.cell_data.shape[3], in_data.shape[2])
        self.cell_frame = cell_frame
        return True

    def transform(self, in_frame, out_frame):
        data = in_frame.as_numpy(copy=True)
        if not self.get_cell(data):
            return False
        k = in_frame.frame_no % self.cell_data.shape[0]
        cell = self.cell_data[k]
        ylen = min(cell.shape[0], data.shape[0])
        xlen = min(cell.shape[1], data.shape[1])
        comps = min(cell.shape[2], data.shape[2])
        for j in range(ylen):
            for i in range(xlen):
                for c in range(comps):
                    data[j::ylen, i::xlen, c::comps] *= cell[j, i, c]
        out_frame.data = data
        audit = out_frame.metadata.get('audit')
        audit += 'data = Modulate(data)\n'
        audit += '    cell: {\n%s}\n' % (
            self.cell_frame.metadata.get('audit'))
        out_frame.metadata.set('audit', audit)
        return True
