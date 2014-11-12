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

from guild.actor import *
import numpy

from pyctools.core.base import Transformer
from .modulatecore import modulate_frame

class Modulate(Transformer):
    inputs = ['input', 'cell']

    def initialise(self):
        self.set_ready(False)

    @actor_method
    def cell(self, cell_data):
        """cell(cell_data)

        Cell data input.

        :param list cell_data: A list of
            :py:class:`numpy:numpy.ndarray` objects.

        """
        for cell in cell_data.data:
            if not isinstance(cell, numpy.ndarray):
                self.logger.warning('Each cell input must be a numpy array')
                return
            if cell.ndim != 3:
                self.logger.warning('Each cell input must be 3 dimensional')
                return
        self.cell_data = cell_data
        self.cell_count = None
        self.set_ready(True)

    def transform(self, in_frame, out_frame):
        in_data = in_frame.as_numpy(dtype=numpy.float32, dstack=False)
        if self.cell_count != len(self.cell_data.data):
            self.cell_count = len(self.cell_data.data)
            if self.cell_count != 1 and self.cell_count != len(in_data):
                self.logger.warning('Mismatch between %d cells and %d images',
                                    self.cell_count, len(in_data))
        out_frame.data = []
        for c, in_comp in enumerate(in_data):
            cell = self.cell_data.data[c % self.cell_count]
            if cell.size == 1:
                out_comp = in_comp * cell[0, 0, 0]
            else:
                out_comp = numpy.empty(in_comp.shape, dtype=numpy.float32)
                modulate_frame(out_comp, in_comp, cell, in_frame.frame_no)
            out_frame.data.append(out_comp)
        audit = out_frame.metadata.get('audit')
        audit += 'data = Modulate(data)\n'
        audit += '    cell: {\n%s}\n' % (
            self.cell_data.metadata.get('audit'))
        out_frame.metadata.set('audit', audit)
        return True
