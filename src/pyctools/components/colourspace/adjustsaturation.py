#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2019  Pyctools contributors
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

__all__ = ['AdjustSaturation']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigEnum, ConfigFloat
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float
from .matrices import Matrices


class AdjustSaturation(Transformer):
    """Make colours more or less saturated.

    Convert RGB frames to "YUV" (actually YCbCr_), multiply UV by a gain
    factor, then convert back to RGB.

    The ``matrix`` config item chooses the matrix coefficient set. It
    can be ``'601'`` ("`Rec. 601`_", standard definition) or ``'709'``
    ("`Rec. 709`_", high definition and sRGB). In ``'auto'`` mode the
    matrix is chosen according to the number of lines in the image.

    WARNING: this component assumes RGB input and output both have black
    level 0 and white level 255, not the 16..235 range specified in Rec
    601.

    .. _Rec. 601: https://en.wikipedia.org/wiki/Rec._601
    .. _Rec. 709: https://en.wikipedia.org/wiki/Rec._709
    .. _YCbCr:    https://en.wikipedia.org/wiki/YCbCr

    """

    def initialise(self):
        self.config['matrix'] = ConfigEnum(choices=('auto', '601', '709'))
        self.config['saturation'] = ConfigFloat(value=1.0, decimals=2)
        self.last_frame_type = None

    def transform(self, in_frame, out_frame):
        self.update_config()
        matrix = self.config['matrix']
        saturation = self.config['saturation']
        # check input and get data
        RGB = in_frame.as_numpy()
        if RGB.shape[2] != 3:
            self.logger.critical('Cannot convert %s images with %d components',
                                 in_frame.type, RGB.shape[2])
            return False
        if in_frame.type != 'RGB' and in_frame.type != self.last_frame_type:
            self.logger.warning('Expected RGB input, got %s', in_frame.type)
        self.last_frame_type = in_frame.type
        # matrix to YUV
        if matrix == 'auto':
            matrix = ('601', '709')[RGB.shape[0] > 576]
        if matrix == '601':
            in_mat = Matrices.RGBtoYUV_601
            out_mat = Matrices.YUVtoRGB_601
        else:
            in_mat = Matrices.RGBtoYUV_709
            out_mat = Matrices.YUVtoRGB_709
        Y = numpy.dot(RGB, in_mat[0:1].T)
        UV = numpy.dot(RGB, in_mat[1:3].T)
        # apply gain
        UV *= pt_float(saturation)
        # matrix to RGB
        YUV = numpy.dstack((Y, UV))
        out_frame.data = numpy.dot(YUV, out_mat.T)
        # audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = AdjustSaturation(data)\n'
        audit += '    saturation: {}, matrix: {}\n'.format(saturation, matrix)
        out_frame.metadata.set('audit', audit)
        return True
