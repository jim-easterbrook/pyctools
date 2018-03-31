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

__all__ = ['FFT', 'VisualiseFFT']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.components.arithmetic import Arithmetic
from pyctools.core.config import ConfigBool, ConfigEnum, ConfigInt
from pyctools.core.base import Transformer
from pyctools.core.types import pt_complex, pt_float

class FFT(Transformer):
    """Compute Fourier transform.

    The image can be divided into (non-overlapping) tiles of any size.
    It is padded out to an integer number of tiles in each direction. If
    you need overlapping tiles, preprocess your images with the
    :py:class:`Tile` component. If you want to window the data before
    computing the FFT, use the
    :py:class:`~pyctools.components.modulate.Modulate` component with a
    window function from :py:mod:`.window`.

    Inputs can be real or complex. The output type is set by the
    ``output`` config value.

    The :py:class:`VisualiseFFT` component can be used to convert the
    (complex) Fourier transform of a picture into a viewable image.

    The ``submean`` option can be used to reduce the amplitude of the
    "zero frequency" output bin. This can reduce leakage that might mask
    nearby low amplitude frequencies.

    ===========  ====  ====
    Config
    ===========  ====  ====
    ``xtile``    int   Horizontal tile size. If zero a single tile the width of the picture is used.
    ``ytile``    int   Vertical tile size. If zero a single tile the height of the picture is used.
    ``inverse``  bool  FFT or IFFT.
    ``submean``  bool  Subtract mean value of each tile before computing FFT.
    ``output``   str   Can be set to ``complex`` or ``real``.
    ===========  ====  ====

    """
    def initialise(self):
        self.config['xtile'] = ConfigInt(min_value=0)
        self.config['ytile'] = ConfigInt(min_value=0)
        self.config['inverse'] = ConfigBool()
        self.config['submean'] = ConfigBool()
        self.config['output'] = ConfigEnum(choices=('complex', 'real'))

    def transform(self, in_frame, out_frame):
        self.update_config()
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        inverse = self.config['inverse']
        submean = self.config['submean']
        out_type = self.config['output']
        in_data = in_frame.as_numpy()
        if not numpy.iscomplexobj(in_data):
            in_data = in_data.astype(pt_float)
        if x_tile == 0:
            x_tile = in_data.shape[1]
        if y_tile == 0:
            y_tile = in_data.shape[0]
        x_blk = (in_data.shape[1] + x_tile - 1) // x_tile
        y_blk = (in_data.shape[0] + y_tile - 1) // y_tile
        x_len = x_blk * x_tile
        y_len = y_blk * y_tile
        x_pad = x_len - in_data.shape[1]
        y_pad = y_len - in_data.shape[0]
        if x_pad or y_pad:
            in_data = numpy.pad(
                in_data, ((0, y_pad), (0, x_pad), (0, 0)), 'constant')
        in_data = in_data.reshape(y_blk, y_tile, x_blk, x_tile, -1)
        if submean:
            in_data -= numpy.mean(in_data, axis=(1, 3), keepdims=True)
        out_data = (numpy.fft.fft2, numpy.fft.ifft2)[inverse](
            in_data, s=(y_tile, x_tile), axes=(1, 3))
        out_data = out_data.astype(pt_complex).reshape(y_len, x_len, -1)
        operation = '%s(data)' % ('FFT', 'IFFT')[inverse]
        if out_type == 'real':
            out_data = numpy.real(out_data)
            operation = 'real(%s)' % operation
        audit = out_frame.metadata.get('audit')
        audit += 'data = %s\n' % operation
        audit += '    tile size: %d x %d\n' % (y_tile, x_tile)
        if submean:
            audit += '    mean subtracted before FT\n'
        out_frame.metadata.set('audit', audit)
        out_frame.data = out_data
        out_frame.type = 'FT'
        return True


def VisualiseFFT(config={}):
    """Convert output of :py:class:`FFT` to a viewable image.

    Computes the logarithmic magnitude of a complex FT and scales to
    0..255 range.

    """
    return Arithmetic(
        config=config,
        func='(numpy.log(numpy.maximum(numpy.absolute(data), 0.0001)) * pt_float(15.0)) + pt_float(40.0)')
