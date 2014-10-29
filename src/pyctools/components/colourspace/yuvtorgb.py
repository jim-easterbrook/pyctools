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

"""YUV (YCbCr) to RGB converter.

Convert YUV frames (with any UV subsampling) to RGB. The conversion
can use a "Rec 601" or "Rec 709" matrix. In "auto" mode the matrix is
chosen according to the number of lines in the image.

The output range can be "studio" (16..235) or "computer" (0..255).
Values are not clipped in either case.

"""

from __future__ import print_function

__all__ = ['YUVtoRGB']

import logging
import sys
import time

import cv2
from guild.actor import *
import numpy

from pyctools.core import Transformer, ConfigEnum
from ..interp.resize import resize_frame

class YUVtoRGB(Transformer):
    mat_601 = numpy.array([[1.0,  0.0,       1.37071],
                           [1.0, -0.336455, -0.698196],
                           [1.0,  1.73245,   0.0]], dtype=numpy.float32)
    mat_709 = numpy.array([[1.0,  0.0,       1.539648],
                           [1.0, -0.183143, -0.457675],
                           [1.0,  1.81418,   0.0]], dtype=numpy.float32)
    filter_21 = numpy.array([[
        -0.002913300, 0.0,  0.010153700, 0.0, -0.022357799, 0.0,
         0.044929001, 0.0, -0.093861297, 0.0,  0.314049691, 0.5,
         0.314049691, 0.0, -0.093861297, 0.0,  0.044929001, 0.0,
        -0.022357799, 0.0,  0.010153700, 0.0, -0.002913300
        ]], dtype=numpy.float32)

    def initialise(self):
        self.config['matrix'] = ConfigEnum(('auto', '601', '709'), dynamic=True)
        self.config['range'] = ConfigEnum(('studio', 'computer'), dynamic=True)
        self.last_frame_type = None

    def transform(self, in_frame, out_frame):
        self.update_config()
        # check input and get data
        data = in_frame.as_numpy(dtype=numpy.float32, dstack=False)
        if len(data) != 3:
            self.logger.critical('Cannot convert %s images with %d components',
                                 in_frame.type, len(data))
            return False
        if in_frame.type != 'YCbCr' and in_frame.type != self.last_frame_type:
            self.logger.warning('Expected YCbCr input, got %s', in_frame.type)
        self.last_frame_type = in_frame.type
        Y_data, U_data, V_data = data
        audit = out_frame.metadata.get('audit')
        audit += 'data = YUVtoRGB(data)\n'
        # apply offset
        Y_data = Y_data - 16.0
        # resample U & V
        v_ss = Y_data.shape[0] // U_data.shape[0]
        h_ss = Y_data.shape[1] // U_data.shape[1]
        if h_ss == 2:
            U_data = resize_frame(U_data, self.filter_21, 2, 1, 1, 1)
            V_data = resize_frame(V_data, self.filter_21, 2, 1, 1, 1)
        elif h_ss != 1:
            U_data = cv2.resize(
                U_data, None, fx=h_ss, fy=1, interpolation=cv2.INTER_CUBIC)
            V_data = cv2.resize(
                V_data, None, fx=h_ss, fy=1, interpolation=cv2.INTER_CUBIC)
        if v_ss != 1:
            U_data = cv2.resize(
                U_data, None, fx=1, fy=v_ss, interpolation=cv2.INTER_CUBIC)
            V_data = cv2.resize(
                V_data, None, fx=1, fy=v_ss, interpolation=cv2.INTER_CUBIC)
        # matrix to RGB
        audit += '    range: %s' % (self.config['range'])
        if (self.config['matrix'] == '601' or
                (self.config['matrix'] == 'auto' and Y_data.shape[0] <= 576)):
            matrix = self.mat_601
            audit += ', matrix: 601\n'
        else:
            matrix = self.mat_709
            audit += ', matrix: 709\n'
        YUV = numpy.dstack((Y_data, U_data, V_data))
        RGB = numpy.dot(YUV, matrix.T)
        # offset or scale
        if self.config['range'] == 'studio':
            RGB += 16.0
        else:
            RGB *= (255.0 / 219.0)
        out_frame.data = [RGB]
        out_frame.type = 'RGB'
        out_frame.metadata.set('audit', audit)
        return True

def main():
    from ..io.rawfilereader import RawFileReader
    class Sink(Actor):
        @actor_method
        def input(self, frame):
            print('sink', frame.frame_no)
            if frame.frame_no == 0:
                frame.as_PIL()[0].show()
##            time.sleep(1.0)

    if len(sys.argv) != 2:
        print('usage: %s yuv_video_file' % sys.argv[0])
        return 1
    logging.basicConfig(level=logging.DEBUG)
    print('YUVtoRGB demonstration')
    source = RawFileReader()
    config = source.get_config()
    config['path'] = sys.argv[1]
    source.set_config(config)
    conv = YUVtoRGB()
    sink = Sink()
    pipeline(source, conv, sink)
    start(source, conv, sink)
    time.sleep(10)
    stop(source, conv, sink)
    wait_for(source, conv, sink)
    return 0

if __name__ == '__main__':
    sys.exit(main())
