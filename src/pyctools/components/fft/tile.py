#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-18  Pyctools contributors
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

__all__ = ['Tile', 'UnTile']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.base import Transformer
from pyctools.core.config import ConfigInt

class Tile(Transformer):
    """Arrange image in overlapping tiles.

    This can be used with the
    :py:class:`~pyctools.components.fft.fft.FFT` component if you need
    FFTs of overlapping tiles, so you can reconstruct an image later on
    without visible tile edges.

    The ``xoff`` and ``yoff`` configuration sets the distance from the
    edge of one tile to the same edge on the next. For complete overlap
    they are usually set to half the tile width & height.

    These parameters are added to the output frame's metadata for use by
    :py:class:`UnTile`.

    =========  ===  ====
    Config
    =========  ===  ====
    ``xtile``  int  Horizontal tile size.
    ``ytile``  int  Vertical tile size.
    ``xoff``   int  Horizontal tile offset. Typically set to xtile // 2.
    ``yoff``   int  Vertical tile offset. Typically set to ytile // 2.
    =========  ===  ====

    """
    def initialise(self):
        self.config['xtile'] = ConfigInt(min_value=1)
        self.config['ytile'] = ConfigInt(min_value=1)
        self.config['xoff'] = ConfigInt(min_value=1)
        self.config['yoff'] = ConfigInt(min_value=1)

    def transform(self, in_frame, out_frame):
        self.update_config()
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        x_off = self.config['xoff']
        y_off = self.config['yoff']
        audit = out_frame.metadata.get('audit')
        audit += 'data = Tile(data)\n'
        audit += '    size: %d x %d, offset: %d x %d\n' % (
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
    """Rearrange overlapping tiles to form an image.

    Inverse operation of the :py:class:`Tile` component. The tile size
    and offset parameters are read from the input image's metadata.

    """
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
        audit += '    size: %d x %d, offset: %d x %d\n' % (
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
