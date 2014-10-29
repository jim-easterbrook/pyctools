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

"""RGB to YUV (YCbCr) converter.

Convert RGB frames to YUV (with 4:4:4 sampling. The conversion
can use a "Rec 601" or "Rec 709" matrix. In "auto" mode the matrix is
chosen according to the number of lines in the image.

The input range can be "studio" (16..235) or "computer" (0..255).

"""

__all__ = ['RGBtoYUV']

from guild.actor import *
import numpy

from pyctools.core import Transformer, ConfigEnum

class RGBtoYUV(Transformer):
    mat_601 = numpy.array(
        [[ 0.299,      0.587,      0.114],
         [-0.1725883, -0.3388272,  0.5114155],
         [ 0.5114155, -0.4282466, -0.0831689]], dtype=numpy.float32)
    mat_709 = numpy.array(
        [[ 0.2126,    0.7152,    0.0722],
         [-0.117188, -0.394228,  0.511415],
         [ 0.511415, -0.464522, -0.046894]], dtype=numpy.float32)

    def initialise(self):
        self.config['matrix'] = ConfigEnum(('auto', '601', '709'), dynamic=True)
        self.config['range'] = ConfigEnum(('studio', 'computer'), dynamic=True)
        self.last_frame_type = None

    def transform(self, in_frame, out_frame):
        self.update_config()
        # check input and get data
        RGB = in_frame.as_numpy(dtype=numpy.float32, dstack=True)[0]
        if RGB.shape[2] != 3:
            self.logger.critical('Cannot convert %s images with %d components',
                                 in_frame.type, RGB.shape[2])
            return False
        if in_frame.type != 'RGB' and in_frame.type != self.last_frame_type:
            self.logger.warning('Expected RGB input, got %s', in_frame.type)
        self.last_frame_type = in_frame.type
        audit = out_frame.metadata.get('audit')
        audit += 'data = RGBtoYUV(data)\n'
        # offset or scale
        if self.config['range'] == 'studio':
            RGB = RGB - 16.0
        else:
            RGB = RGB * (219.0 / 255.0)
        # matrix to YUV
        audit += '    range: %s' % (self.config['range'])
        if (self.config['matrix'] == '601' or
                (self.config['matrix'] == 'auto' and RGB.shape[0] <= 576)):
            matrix = self.mat_601
            audit += ', matrix: 601\n'
        else:
            matrix = self.mat_709
            audit += ', matrix: 709\n'
        out_frame.data = [
            numpy.dot(RGB, matrix[0].T) + 16.0,
            numpy.dot(RGB, matrix[1].T),
            numpy.dot(RGB, matrix[2].T),
            ]
        out_frame.type = 'YCbCr'
        out_frame.metadata.set('audit', audit)
        return True
