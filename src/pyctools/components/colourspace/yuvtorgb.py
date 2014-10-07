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

Convert YUV frames (with any UV subsampling) to RGB.

"""

from __future__ import print_function

import logging
import sys
import time

from guild.actor import *
import numpy
from PIL import Image
import scipy.ndimage

from ...core import Transformer

class YUVtoRGB(Transformer):
    def transform(self, in_frame, out_frame):
        # check input and get data
        if len(in_frame.data) != 3 or in_frame.type != 'YCbCr':
            raise RuntimeError('Cannot convert "%s" images.' % in_frame.type)
        Y_data, U_data, V_data = in_frame.as_numpy()
        # correct offset (and promote to floating format)
        U_data = U_data - 128.0
        V_data = V_data - 128.0
        # resample U & V
        v_ss = Y_data.shape[0] // U_data.shape[0]
        h_ss = Y_data.shape[1] // U_data.shape[1]
        if v_ss != 1 or h_ss != 1:
            U_data = scipy.ndimage.zoom(U_data, (v_ss, h_ss))
            V_data = scipy.ndimage.zoom(V_data, (v_ss, h_ss))
        # matrix (the hard way)
        R_data = Y_data + (V_data * 1.37071)
        G_data = Y_data - (U_data * 0.336455) - (V_data * 0.698196)
        B_data = Y_data + (U_data * 1.73245)
        # merge using PIL
        R_data = R_data.astype(numpy.uint8)
        G_data = G_data.astype(numpy.uint8)
        B_data = B_data.astype(numpy.uint8)
        out_frame.data.append(Image.merge('RGB', (Image.fromarray(R_data),
                                                  Image.fromarray(G_data),
                                                  Image.fromarray(B_data))))
        out_frame.type = 'RGB'

def main():
    from ..io.rawfilereader import RawFileReader
    class Sink(Actor):
        @actor_method
        def input(self, frame):
            print('sink', frame.frame_no)
            if frame.frame_no == 0:
                frame.data[0].show()
            time.sleep(1.0)

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
