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

Convert RGB frames to "YUV" (actually YCbCr) with 4:4:4 sampling.

The ``matrix`` config item chooses the matrix coefficient set. It can
be ``'601'`` ("Rec 601", standard definition) or ``'709'`` ("Rec 709",
high definition). In ``'auto'`` mode the matrix is chosen according to
the number of lines in the image.

The ``range`` config item specifies the input video range. It can be
either ``'studio'`` (16..235) or ``'computer'`` (0..255). Values are
not clipped in either case.

"""

__all__ = ['RGBtoYUV']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigEnum
from pyctools.core.base import Component
from pyctools.core.types import pt_float

class RGBtoYUV(Component):
    mat_601 = numpy.array(
        [[ 0.299,      0.587,      0.114],
         [-0.1725883, -0.3388272,  0.5114155],
         [ 0.5114155, -0.4282466, -0.0831689]], dtype=pt_float)
    mat_709 = numpy.array(
        [[ 0.2126,    0.7152,    0.0722],
         [-0.117188, -0.394228,  0.511415],
         [ 0.511415, -0.464522, -0.046894]], dtype=pt_float)
    outputs = ['output_Y', 'output_UV']
    with_outframe_pool = True

    def initialise(self):
        self.config['matrix'] = ConfigEnum(('auto', '601', '709'), dynamic=True)
        self.config['range'] = ConfigEnum(('studio', 'computer'), dynamic=True)
        self.last_frame_type = None

    def process_frame(self):
        in_frame = self.input_buffer['input'].get()
        Y_frame = self.outframe_pool['output_Y'].get()
        Y_frame.initialise(in_frame)
        UV_frame = self.outframe_pool['output_UV'].get()
        UV_frame.initialise(in_frame)
        if self.transform(in_frame, Y_frame, UV_frame):
            self.output_Y(Y_frame)
            self.output_UV(UV_frame)
        else:
            self.output_Y(None)
            self.output_UV(None)
            self.stop()
            return

    def transform(self, in_frame, Y_frame, UV_frame):
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
        Y_audit = Y_frame.metadata.get('audit')
        Y_audit += 'data = RGBtoY(data)\n'
        UV_audit = UV_frame.metadata.get('audit')
        UV_audit += 'data = RGBtoUV(data)\n'
        # offset or scale
        if self.config['range'] == 'studio':
            RGB = RGB - pt_float(16.0)
        else:
            RGB = RGB * pt_float(219.0 / 255.0)
        # matrix to YUV
        Y_audit += '    range: %s' % (self.config['range'])
        UV_audit += '    range: %s' % (self.config['range'])
        if (self.config['matrix'] == '601' or
                (self.config['matrix'] == 'auto' and RGB.shape[0] <= 576)):
            matrix = self.mat_601
            Y_audit += ', matrix: 601\n'
            UV_audit += ', matrix: 601\n'
        else:
            matrix = self.mat_709
            Y_audit += ', matrix: 709\n'
            UV_audit += ', matrix: 709\n'
        Y_frame.data = numpy.dot(RGB, matrix[0:1].T) + pt_float(16.0)
        UV_frame.data = numpy.dot(RGB, matrix[1:3].T)
        Y_frame.type = 'Y'
        UV_frame.type = 'CbCr'
        Y_frame.metadata.set('audit', Y_audit)
        UV_frame.metadata.set('audit', UV_audit)
        return True
