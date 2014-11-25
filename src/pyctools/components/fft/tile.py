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

"""Arrange image in (overlapping) tiles.

"""

__all__ = ['Tile', 'UnTile', 'CrossFade']
__docformat__ = 'restructuredtext en'

import numpy
import sys
import time
if 'sphinx' in sys.modules:
    __all__.append('CrossFadeCore')

from pyctools.core.base import Component, Transformer
from pyctools.core.config import ConfigInt
from pyctools.core.frame import Frame

class Tile(Transformer):
    def initialise(self):
        self.config['xlen'] = ConfigInt(min_value=1, dynamic=True)
        self.config['ylen'] = ConfigInt(min_value=1, dynamic=True)
        self.config['xinc'] = ConfigInt(min_value=1, dynamic=True)
        self.config['yinc'] = ConfigInt(min_value=1, dynamic=True)

    def transform(self, in_frame, out_frame):
        self.update_config()
        x_tile = self.config['xlen']
        y_tile = self.config['ylen']
        x_off = self.config['xinc']
        y_off = self.config['yinc']
        audit = out_frame.metadata.get('audit')
        audit += 'data = Tile(data)\n'
        audit += '    size = %d x %d, offset = %d x %d\n' % (
            y_tile, x_tile, y_off, x_off)
        out_frame.metadata.set('audit', audit)
        data = in_frame.as_numpy()
        tile_params = eval(out_frame.metadata.get('tile', '[]'))
        tile_params.append(
            (y_tile, x_tile, y_off, x_off, data.shape[0], data.shape[1]))
        out_frame.metadata.set('tile', repr(tile_params))
        x_mgn = (x_tile - 1) // x_off
        y_mgn = (y_tile - 1) // y_off
        x_blk = ((data.shape[1] + x_off - 1) // x_off) + x_mgn
        y_blk = ((data.shape[0] + y_off - 1) // y_off) + y_mgn
        out_data = numpy.zeros(
            [y_tile * y_blk, x_tile * x_blk] + list(data.shape[2:]),
            dtype=data.dtype)
        for j in range(y_blk):
            yi_0 = (j - y_mgn) * y_off
            yo_0 = j * y_tile
            yi_1 = yi_0 + y_tile
            yo_1 = yo_0 + y_tile
            if yi_0 < 0:
                yo_0 -= yi_0
                yi_0 = 0
            if yi_1 > data.shape[0]:
                yo_1 -= yi_1 - data.shape[0]
                yi_1 = data.shape[0]
            for i in range(x_blk):
                xi_0 = (i - x_mgn) * x_off
                xo_0 = i * x_tile
                xi_1 = xi_0 + x_tile
                xo_1 = xo_0 + x_tile
                if xi_0 < 0:
                    xo_0 -= xi_0
                    xi_0 = 0
                if xi_1 > data.shape[1]:
                    xo_1 -= xi_1 - data.shape[1]
                    xi_1 = data.shape[1]
                out_data[yo_0:yo_1, xo_0:xo_1] = data[yi_0:yi_1, xi_0:xi_1]
        out_frame.data = out_data
        return True


class UnTile(Transformer):
    def transform(self, in_frame, out_frame):
        data = in_frame.as_numpy()
        tile_params = eval(out_frame.metadata.get('tile', '[]'))
        if not tile_params:
            self.logger.error('Input has no "tile" metadata')
            return False
        y_tile, x_tile, y_off, x_off, height, width = tile_params.pop()
        out_frame.metadata.set('tile', repr(tile_params))
        audit = out_frame.metadata.get('audit')
        audit += 'data = UnTile(data)\n'
        audit += '    size = %d x %d, offset = %d x %d\n' % (
            y_tile, x_tile, y_off, x_off)
        out_frame.metadata.set('audit', audit)
        x_mgn = (x_tile - 1) // x_off
        y_mgn = (y_tile - 1) // y_off
        x_blk = data.shape[1] // x_tile
        y_blk = data.shape[0] // y_tile
        out_data = numpy.zeros(
            [height, width] + list(data.shape[2:]), dtype=data.dtype)
        for j in range(y_blk):
            yi_0 = j * y_tile
            yo_0 = (j - y_mgn) * y_off
            yi_1 = yi_0 + y_tile
            yo_1 = yo_0 + y_tile
            if yo_0 < 0:
                yi_0 -= yo_0
                yo_0 = 0
            if yo_1 > out_data.shape[0]:
                yi_1 -= yo_1 - out_data.shape[0]
                yo_1 = out_data.shape[0]
            for i in range(x_blk):
                xi_0 = i * x_tile
                xo_0 = (i - x_mgn) * x_off
                xi_1 = xi_0 + x_tile
                xo_1 = xo_0 + x_tile
                if xo_0 < 0:
                    xi_0 -= xo_0
                    xo_0 = 0
                if xo_1 > out_data.shape[1]:
                    xi_1 -= xo_1 - out_data.shape[1]
                    xo_1 = out_data.shape[1]
                out_data[yo_0:yo_1, xo_0:xo_1] += data[yi_0:yi_1, xi_0:xi_1]
        out_frame.data = out_data
        return True


class CrossFade(Component):
    inputs = []

    def initialise(self):
        self.config['xlen'] = ConfigInt(min_value=1, dynamic=True)
        self.config['ylen'] = ConfigInt(min_value=1, dynamic=True)
        self.config['xinc'] = ConfigInt(min_value=1, dynamic=True)
        self.config['yinc'] = ConfigInt(min_value=1, dynamic=True)

    def gen_process(self):
        # wait for self.output to be connected
        while self.output.__self__ == self:
            yield 1
            time.sleep(0.01)
        # send first cell
        self.update_config()
        self.make_cell()
        # send more cells if config changes
        while True:
            yield 1
            time.sleep(0.1)
            if self.update_config():
                self.make_cell()

    def make_cell(self):
        x_tile = self.config['xlen']
        y_tile = self.config['ylen']
        x_off = self.config['xinc']
        y_off = self.config['yinc']
        self.output(CrossFadeCore(
            x_tile=x_tile, x_off=x_off, y_tile=y_tile, y_off=y_off))


def CrossFadeCore(x_tile=1, x_off=1, y_tile=1, y_off=1):
    """

    :return: A :py:class:`~pyctools.core.frame.Frame` object containing the
        cell.

    """
    def cell_1D(tile, offset):
        result = numpy.ones([tile], dtype=numpy.float32)
        overlap = tile - offset
        for i in range(overlap):
            result[i] = numpy.float32(i + 1) / numpy.float32(overlap + 1)
            result[(tile - 1) - i] = result[i]
        return result

    x_cell = cell_1D(x_tile, x_off)
    y_cell = cell_1D(y_tile, y_off)
    result = numpy.empty(
        [1, y_cell.shape[0], x_cell.shape[0], 1], dtype=numpy.float32)
    for y in range(result.shape[1]):
        for x in range(result.shape[2]):
            result[0, y, x, 0] = x_cell[x] * y_cell[y]
    out_frame = Frame()
    out_frame.data = result
    out_frame.type = 'cell'
    audit = out_frame.metadata.get('audit')
    audit += 'data = CrossFadeCell()\n'
    audit += '    size = %d x %d, offset = %d x %d\n' % (
        y_tile, x_tile, y_off, x_off)
    out_frame.metadata.set('audit', audit)
    return out_frame
