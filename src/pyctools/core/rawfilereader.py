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

"""Raw file reader.

"""

from __future__ import print_function

import io
import logging
import sys
import time

from guild.actor import *
from numpy import array
import numpy

from pyctools.core.objectpool import ObjectPool

class Frame(object):
    pass

bytes_per_pixel = {
    'UYVY' : 2,
    }

mux_layout = {
    'UYVY' : (1, 0, 2, 2),
    }

class RawFileReader(Actor):
    def __init__(self, xlen, ylen, fourcc, path):
        super(RawFileReader, self).__init__()
        self.xlen = xlen
        self.ylen = ylen
        self.fourcc = fourcc
        self.path = path
        if self.fourcc not in bytes_per_pixel:
            raise RuntimeError("Can't open %s files" % self.fourcc)

    def process_start(self):
        self.frame_size = self.xlen * self.ylen * bytes_per_pixel[self.fourcc]
        self.file = io.open(self.path, 'rb', 0)
        self.frame_no = 0
        self.pool = ObjectPool(Frame, 3)
        self.pool.bind("output", self, "new_frame")
        start(self.pool)

    @actor_method
    def new_frame(self, frame):
        raw_data = self.file.read(self.frame_size)
        if len(raw_data) < self.frame_size:
            self.stop()
            return
        # convert to numpy arrays
        Yoff, Uoff, Voff, UVhss = mux_layout[self.fourcc]
        raw_array = numpy.frombuffer(raw_data, numpy.uint8)
        frame.Y_data = raw_array[Yoff::2].reshape(self.ylen, self.xlen)
        frame.U_data = raw_array[Uoff::4].reshape(self.ylen, self.xlen // 2)
        frame.V_data = raw_array[Voff::4].reshape(self.ylen, self.xlen // 2)
        frame.frame_no = self.frame_no
        self.frame_no += 1
        self.output(frame)

    def onStop(self):
        stop(self.pool)
        self.file.close()

def main():
    from pyctools.core.yuvtorgb import YUVtoRGB
    class Sink(Actor):
        @actor_method
        def input(self, frame):
            print('sink', frame.frame_no)
            if frame.frame_no == 0:
                frame.image.show()
            time.sleep(1.0)

    if len(sys.argv) != 2:
        print('usage: %s uyvy_video_file' % sys.argv[0])
        return 1
    logging.basicConfig(level=logging.DEBUG)
    print('RawFileReader demonstration')
    source = RawFileReader(1920, 1080, 'UYVY', sys.argv[1])
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
