#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-20  Pyctools contributors
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
        in_data = in_frame.as_numpy()
        y_len, x_len = in_data.shape[:2]
        tile_params = eval(out_frame.metadata.get('tile', '[]'))
        tile_params.append((y_tile, x_tile, y_off, x_off, y_len, x_len))
        out_frame.metadata.set('tile', repr(tile_params))
        if x_tile in (1, x_off):
            # no overlap, so nothing to do
            x_tile = x_len
            x_off = x_tile
        if y_tile in (1, y_off):
            # no overlap, so nothing to do
            y_tile = y_len
            y_off = y_tile
        x_mgn = (x_tile - 1) // x_off
        y_mgn = (y_tile - 1) // y_off
        x_blk = (x_len + x_off - 1) // x_off
        y_blk = (y_len + y_off - 1) // y_off
        pad_width = ((y_mgn * y_off, y_tile + ((y_blk - 1) * y_off) - y_len),
                     (x_mgn * x_off, x_tile + ((x_blk - 1) * x_off) - x_len),
                     (0, 0))
        x_blk += x_mgn
        y_blk += y_mgn
        if numpy.any(pad_width):
            in_data = numpy.pad(in_data, pad_width)
        out_data = numpy.empty(
            [y_blk, y_tile, x_blk, x_tile] + list(in_data.shape[2:]),
            dtype=in_data.dtype)
        y = 0
        for j in range(y_blk):
            x = 0
            for i in range(x_blk):
                out_data[j, ::, i, ::] = in_data[y:y+y_tile, x:x+x_tile]
                x += x_off
            y += y_off
        out_frame.data = out_data.reshape((y_blk * y_tile, x_blk * x_tile, -1))
        return True


class UnTile(Transformer):
    """Rearrange overlapping tiles to form an image.

    Inverse operation of the :py:class:`Tile` component. The tile size
    and offset parameters are read from the input image's metadata.

    """
    def transform(self, in_frame, out_frame):
        in_data = in_frame.as_numpy()
        tile_params = eval(out_frame.metadata.get('tile', '[]'))
        if not tile_params:
            self.logger.error('Input has no "tile" metadata')
            return False
        y_tile, x_tile, y_off, x_off, y_len, x_len = tile_params.pop()
        out_frame.metadata.set('tile', repr(tile_params))
        audit = out_frame.metadata.get('audit')
        audit += 'data = UnTile(data)\n'
        audit += '    size: %d x %d, offset: %d x %d\n' % (
            y_tile, x_tile, y_off, x_off)
        out_frame.metadata.set('audit', audit)
        if x_tile in (1, x_off):
            # no overlap, so nothing to do
            x_tile = x_len
            x_off = x_tile
        if y_tile in (1, y_off):
            # no overlap, so nothing to do
            y_tile = y_len
            y_off = y_tile
        x_mgn = (x_tile - 1) // x_off
        y_mgn = (y_tile - 1) // y_off
        x_blk = in_data.shape[1] // x_tile
        y_blk = in_data.shape[0] // y_tile
        out_data = numpy.zeros([y_tile + ((y_blk - 1) * y_off),
                                x_tile + ((x_blk - 1) * x_off)]
                               + list(in_data.shape[2:]), dtype=in_data.dtype)
        in_data = in_data.reshape((y_blk, y_tile, x_blk, x_tile, -1))
        y = 0
        for j in range(y_blk):
            x = 0
            for i in range(x_blk):
                out_data[y:y+y_tile, x:x+x_tile] += in_data[j, ::, i, ::]
                x += x_off
            y += y_off
        x = x_mgn * x_off
        y = y_mgn * y_off
        out_frame.data = out_data[y:y+y_len, x:x+x_len, ::].copy()
        return True
