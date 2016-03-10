#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2016  Pyctools contributors
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

__all__ = ['PlotData']
__docformat__ = 'restructuredtext en'

import matplotlib.pyplot as plt

from pyctools.core.base import Component
from pyctools.core.qt import QtEventLoop

class PlotData(Component):
    """Plot data on a graph.

    The input frame's data should be a 2-D
    :py:class:`numpy:numpy.ndarray`. The first row contains horizontal
    (X) coordinates and the remaining rows contain corresponding Y
    values.

    """
    with_outframe_pool = False
    outputs = []
    event_loop = QtEventLoop

    def initialise(self):
        self.lines = []

    def process_frame(self):
        in_frame = self.input_buffer['input'].get()
        data = in_frame.as_numpy()
        x = data[0]
        if self.lines:
            for i, y in enumerate(data[1:]):
                self.lines[i].set_xdata(x)
                self.lines[i].set_ydata(y)
            plt.draw()
        else:
            plt.ion()
            for y in data[1:]:
                self.lines.append(plt.plot(x, y, '-')[0])
            plt.show()
