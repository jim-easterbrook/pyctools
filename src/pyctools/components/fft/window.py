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

"""FFT window functions.

"""

__all__ = ['Hanning', 'Hamming', 'InverseWindow']
__docformat__ = 'restructuredtext en'

import math
import numpy
import sys
import time
if 'sphinx' in sys.modules:
    __all__.append('HanningCore', 'HammingCore')

from pyctools.core.base import Component
from pyctools.core.config import ConfigEnum, ConfigInt
from pyctools.core.frame import Frame

class WindowBase(Component):
    inputs = []

    def initialise(self):
        self.config['xtile'] = ConfigInt(min_value=1, dynamic=True)
        self.config['ytile'] = ConfigInt(min_value=1, dynamic=True)

    def gen_process(self):
        # wait for self.output to be connected
        while self.output.__self__ == self:
            yield 1
            time.sleep(0.01)
        # send first window
        self.update_config()
        self.make_window()
        # send more windows if config changes
        while True:
            yield 1
            time.sleep(0.1)
            if self.update_config():
                self.make_window()


class Hanning(WindowBase):
    def make_window(self):
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        self.output(HanningCore(x_tile=x_tile, y_tile=y_tile))


class Hamming(WindowBase):
    def make_window(self):
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        self.output(HammingCore(x_tile=x_tile, y_tile=y_tile))


def Window2D(name, x_tile, y_tile, function_1D, x_params={}, y_params={}):
    if x_tile == 1:
        x_win = numpy.array([1.0], dtype=numpy.float32)
    else:
        x_win = function_1D(x_tile, **x_params)
    if y_tile == 1:
        y_win = numpy.array([1.0], dtype=numpy.float32)
    else:
        y_win = function_1D(y_tile, **y_params)
    result = numpy.empty(
        [1, y_win.shape[0], x_win.shape[0], 1], dtype=numpy.float32)
    for y in range(result.shape[1]):
        for x in range(result.shape[2]):
            result[0, y, x, 0] = x_win[x] * y_win[y]
    out_frame = Frame()
    out_frame.data = result
    out_frame.type = 'win'
    audit = out_frame.metadata.get('audit')
    audit += 'data = %sWindow()\n' % name
    audit += '    size: %d x %d\n' % (y_tile, x_tile)
    out_frame.metadata.set('audit', audit)
    return out_frame


def HanningCore(x_tile=1, y_tile=1):
    """

    :return: A :py:class:`~pyctools.core.frame.Frame` object containing the
        window.

    """
    def Hanning_1D(tile):
        result = numpy.ndarray([tile], dtype=numpy.float32)
        for i in range(tile):
            result[i] = 0.5 + (0.5 * math.cos(
                math.pi * float((i * 2) + tile - 1) / float(tile - 1)))
        return result

    return Window2D('Hanning', x_tile, y_tile, Hanning_1D)


def HammingCore(x_tile=1, y_tile=1):
    """

    :return: A :py:class:`~pyctools.core.frame.Frame` object containing the
        window.

    """
    def Hamming_1D(tile):
        result = numpy.ndarray([tile], dtype=numpy.float32)
        for i in range(tile):
            result[i] = 0.53836 + (0.46164 * math.cos(
                math.pi * float((i * 2) + tile - 1) / float(tile - 1)))
        return result

    return Window2D('Hamming', x_tile, y_tile, Hamming_1D)


class InverseWindow(Component):
    with_outframe_pool = False

    def initialise(self):
        self.config['xtile'] = ConfigInt(min_value=1, dynamic=True)
        self.config['ytile'] = ConfigInt(min_value=1, dynamic=True)
        self.config['xoff'] = ConfigInt(min_value=1, dynamic=True)
        self.config['yoff'] = ConfigInt(min_value=1, dynamic=True)
        self.config['fade'] = ConfigEnum(choices=(
            'switch', 'linear', 'minsnr'), dynamic=True)

    def process_frame(self):
        self.update_config()
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        x_off = self.config['xoff']
        y_off = self.config['yoff']
        fade = self.config['fade']
        in_frame = self.input_buffer['input'].get()
        out_frame = Frame()
        out_frame.initialise(in_frame)
        audit = out_frame.metadata.get('audit')
        audit += 'data = InverseWindow(data)\n'
        audit += '    size: %d x %d, offset: %d x %d\n' % (
            y_tile, x_tile, y_off, x_off)
        audit += '    fade: %s\n' % fade
        out_frame.metadata.set('audit', audit)

        in_data = in_frame.as_numpy(dtype=numpy.float32)
        result = numpy.empty(in_data.shape, dtype=numpy.float32)
        x_overlap = x_tile - x_off
        y_overlap = y_tile - y_off
        for y in range(y_tile):
            y0 = y
            while y0 >= y_off:
                y0 -= y_off
            for x in range(x_tile):
                x0 = x
                while x0 >= x_off:
                    x0 -= x_off
                # get window value of this and neighbouring tiles
                centre = in_data[0, y, x, 0]
                neighbours = []
                for j in range(y0, y_tile, y_off):
                    for i in range(x0, x_tile, x_off):
                        if j == y and i == x:
                            continue
                        neighbours.append(in_data[0, j, i, 0])
                if not neighbours:
                    result[0, y, x, 0] = 1.0 / max(centre, 0.000001)
                elif fade == 'minsnr':
                    result[0, y, x, 0] = centre / (
                        (centre ** 2) + sum(map(lambda x: x ** 2, neighbours)))
                elif fade == 'linear':
                    result[0, y, x, 0] = 1.0 / (centre + sum(neighbours))
                else:
                    biggest = max(neighbours)
                    if centre > biggest:
                        result[0, y, x, 0] = 1.0 / max(centre, 0.000001)
                    elif centre < biggest:
                        result[0, y, x, 0] = 0.0
                    else:
                        result[0, y, x, 0] = 0.5 / max(centre, 0.000001)
        out_frame.data = result
        self.output(out_frame)
