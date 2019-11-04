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

__all__ = ['MedianFilter']
__docformat__ = 'restructuredtext en'

import cv2
import numpy

from pyctools.core.base import Transformer
from pyctools.core.config import ConfigEnum, ConfigInt
from pyctools.core.types import pt_float
from pyctools.components.colourspace.matrices import Matrices


class MedianFilter(Transformer):
    """Median filter image denoising.

    RGB inputs are converted to "YUV" (Actually YCbCr_) so different
    filter sizes can be used on luminance and chrominance. The
    ``matrix`` config item chooses the matrix coefficient set. It can be
    ``'601'`` ("`Rec. 601`_", standard definition) or ``'709'`` ("`Rec.
    709`_", high definition). In ``'auto'`` mode the matrix is chosen
    according to the number of lines in the image.

    WARNING: this component assumes the RGB input has black level 0 and
    white level 255, not the 16..235 range specified in Rec 601/709. See
    :py:mod:`pyctools.components.colourspace.levels` for components to
    convert the RGB input and output.

    The filter used is OpenCV's medianBlur_. For radius values greater
    than two the image data is converted to 8-bit. Hence the filter is
    best used on "gamma-corrected" images rather than linear.

    Config:

    =============  ===  ====
    ``radius_Y``   int  Luminance filter size.
    ``radius_UV``  int  Chrominance filter size.
    ``matrix``     str  RGB<->YUV matrix.
    =============  ===  ====

    .. _Rec. 601:   https://en.wikipedia.org/wiki/Rec._601
    .. _Rec. 709:   https://en.wikipedia.org/wiki/Rec._709
    .. _YCbCr:      https://en.wikipedia.org/wiki/YCbCr
    .. _medianBlur: https://docs.opencv.org/2.4/modules/imgproc/doc/filtering.html#medianblur

    """

    def initialise(self):
        self.config['radius_Y'] = ConfigInt(value=1, min_value=0)
        self.config['radius_UV'] = ConfigInt(value=1, min_value=0)
        self.config['matrix'] = ConfigEnum(choices=('auto', '601', '709'))

    def transform(self, in_frame, out_frame):
        self.update_config()
        matrix = self.config['matrix']
        radius_Y = self.config['radius_Y']
        radius_UV = self.config['radius_UV']
        # check input and get data
        RGB = in_frame.as_numpy(dtype=pt_float)
        if RGB.shape[2] != 3:
            self.logger.critical('Cannot process %s images with %d components',
                                 in_frame.type, RGB.shape[2])
            return False
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
        U = numpy.dot(RGB, in_mat[1:2].T)
        V = numpy.dot(RGB, in_mat[2:3].T)
        # process Y
        ksize = 1 + (radius_Y * 2)
        if ksize > 5:
            # convert to 8 bit
            Y = Y.clip(0, 255).astype(numpy.uint8)
        if ksize == 1:
            pass
        else:
            Y = cv2.medianBlur(Y, ksize)
        # process UV
        ksize = 1 + (radius_UV * 2)
        if ksize > 5:
            # add offset and convert to 8 bit
            U += pt_float(128)
            V += pt_float(128)
            U = U.clip(0, 255).astype(numpy.uint8)
            V = V.clip(0, 255).astype(numpy.uint8)
        if ksize > 1:
            U = cv2.medianBlur(U, ksize)
            V = cv2.medianBlur(V, ksize)
        if ksize > 5:
            # subtract offset
            U = U - pt_float(128)
            V = V - pt_float(128)
        # matrix back to RGB
        YUV = numpy.dstack((Y, U, V))
        out_frame.data = numpy.dot(YUV, out_mat.T)
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = MedianFilter(data)\n'
        audit += '    radius_Y: {}, radius_UV: {}, matrix: {}\n'.format(
            radius_Y, radius_UV, matrix)
        out_frame.metadata.set('audit', audit)
        return True
