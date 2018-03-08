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

__all__ = ['RGBtoY']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigEnum
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float
from .rgbtoyuv import RGBtoYUV

class RGBtoY(Transformer):
    """RGB to Y converter.

    Convert RGB frames to luminance.

    The ``matrix`` config item chooses the matrix coefficient set. It
    can be ``'601'`` ("Rec 601", standard definition) or ``'709'`` ("Rec
    709", high definition). In ``'auto'`` mode the matrix is chosen
    according to the number of lines in the image.

    The ``range`` config item specifies the input video range. It can be
    either ``'studio'`` (16..235) or ``'computer'`` (0..255). Values are
    not clipped in either case.

    """

    mat_601 = RGBtoYUV.mat_601[0:1]
    mat_709 = RGBtoYUV.mat_709[0:1]

    def initialise(self):
        self.config['matrix'] = ConfigEnum(choices=('auto', '601', '709'))
        self.config['range'] = ConfigEnum(choices=('studio', 'computer'))
        self.last_frame_type = None

    def transform(self, in_frame, out_frame):
        self.update_config()
        # check input and get data
        RGB = in_frame.as_numpy()
        if RGB.shape[2] != 3:
            self.logger.critical('Cannot convert %s images with %d components',
                                 in_frame.type, RGB.shape[2])
            return False
        if in_frame.type != 'RGB' and in_frame.type != self.last_frame_type:
            self.logger.warning('Expected RGB input, got %s', in_frame.type)
        self.last_frame_type = in_frame.type
        audit = out_frame.metadata.get('audit')
        audit += 'data = RGBtoY(data)\n'
        # offset or scale
        if self.config['range'] == 'studio':
            RGB = RGB - pt_float(16.0)
        else:
            RGB = RGB * pt_float(219.0 / 255.0)
        # matrix to Y
        audit += '    range: %s' % (self.config['range'])
        if (self.config['matrix'] == '601' or
                (self.config['matrix'] == 'auto' and RGB.shape[0] <= 576)):
            matrix = self.mat_601
            audit += ', matrix: 601\n'
        else:
            matrix = self.mat_709
            audit += ', matrix: 709\n'
        out_frame.data = numpy.dot(RGB, matrix.T) + pt_float(16.0)
        out_frame.type = 'Y'
        out_frame.metadata.set('audit', audit)
        return True
