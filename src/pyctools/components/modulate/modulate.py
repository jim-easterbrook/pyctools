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

"""Modulate or sample an image.

Multiplies each pixel value by a modulating value that can vary
horizontally, vertically and temporally. The modulating function is
supplied in a small "cell" whose dimensions should be the repeat
period of the function in each direction.

The :py:meth:`~Modulate.cell` method is used to update the modulating
function. No processing happens until a cell is received, and new
cells can be applied while the component is running.

The cell is supplied as a :py:class:`list` of
:py:class:`numpy:numpy.ndarray` objects. If the list has one member
then the same cell is applied to each component of the input.
Alternatively the list should have one cell for each component,
allowing a different modulation to be applied to each colour.

For example, a cell to simulate a `Bayer filter
<http://en.wikipedia.org/wiki/Bayer_filter>`_ could look like this::

    [array([[[0, 0],
             [0, 1]]]),
     array([[[0, 1],
             [1, 0]]]),
     array([[[1, 0],
             [0, 0]]])]

"""

__all__ = ['Modulate']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.base import Transformer
from .modulatecore import modulate_frame

class Modulate(Transformer):
    inputs = ['input', 'cell']

    def initialise(self):
        self.cell_frame = None

    def get_cell(self):
        cell_frame = self.input_buffer['cell'].peek()
        if cell_frame == self.cell_frame:
            return True
        self.cell_data = cell_frame.as_numpy(dtype=numpy.float32)[0]
        if self.cell_data.ndim != 4:
            self.logger.error('Cell input must be 4 dimensional')
            self.input_buffer['cell'].get()
            return False
        self.cell_frame = cell_frame
        self.cell_count = None
        return True

    def transform(self, in_frame, out_frame):
        if not self.get_cell():
            return False
        in_data = in_frame.as_numpy(dtype=numpy.float32)[0]
        if self.cell_count != self.cell_data.shape[3]:
            self.cell_count = self.cell_data.shape[3]
            if self.cell_count != 1 and self.cell_count != in_data.shape[2]:
                self.logger.warning('Mismatch between %d cells and %d components',
                                    self.cell_count, in_data.shape[2])
        out_frame.data = [
            modulate_frame(in_data, self.cell_data, in_frame.frame_no)]
        audit = out_frame.metadata.get('audit')
        audit += 'data = Modulate(data)\n'
        audit += '    cell: {\n%s}\n' % (
            self.cell_frame.metadata.get('audit'))
        out_frame.metadata.set('audit', audit)
        return True
