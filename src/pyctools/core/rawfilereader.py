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

from guild.actor import *
import numpy

from pyctools.core.frame import Frame
from pyctools.core.objectpool import ObjectPool

bytes_per_pixel = {
    'UYVY' : 2,
    }

mux_layout = {
    'UYVY' : (1, 2, 0, 4, 2, 4, 2),
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
        Yoff, Yps, Uoff, Ups, Voff, Vps, UVhss = mux_layout[self.fourcc]
        raw_array = numpy.frombuffer(raw_data, numpy.uint8)
        Y_data = raw_array[Yoff::Yps]
        U_data = raw_array[Uoff::Ups]
        V_data = raw_array[Voff::Vps]
        frame.data.append(Y_data.reshape(self.ylen, self.xlen))
        frame.data.append(U_data.reshape(self.ylen, self.xlen // UVhss))
        frame.data.append(V_data.reshape(self.ylen, self.xlen // UVhss))
        frame.type = 'YCbCr'
        frame.frame_no = self.frame_no
        self.frame_no += 1
        self.output(frame)

    def onStop(self):
        stop(self.pool)
        self.file.close()

def main():
    import time
    class Sink(Actor):
        @actor_method
        def input(self, frame):
            print('sink', frame.frame_no, end='\r')
            sys.stdout.flush()
            if frame.frame_no == 0:
                self.start_time = time.time()
                self.byte_count = 0
                self.frame_count = 0
            else:
                self.byte_count += frame.data[0].shape[0] * frame.data[0].shape[1]
                self.byte_count += frame.data[1].shape[0] * frame.data[1].shape[1]
                self.byte_count += frame.data[2].shape[0] * frame.data[2].shape[1]
                self.frame_count += 1

        def onStop(self):
            duration = time.time() - self.start_time
            print()
            print('received %d bytes in %g seconds' % (
                self.byte_count, duration))
            print('%d frames of %d bytes each' % (
                self.frame_count, self.byte_count // self.frame_count))
            print('%g frames/second, %g bytes/second' % (
                self.frame_count / duration, self.byte_count / duration))

    if len(sys.argv) != 2:
        print('usage: %s uyvy_video_file' % sys.argv[0])
        return 1
    logging.basicConfig(level=logging.DEBUG)
    print('RawFileReader demonstration')
    source = RawFileReader(1920, 1080, 'UYVY', sys.argv[1])
    sink = Sink()
    pipeline(source, sink)
    start(source, sink)
    wait_for(source)
    time.sleep(1)
    stop(source, sink)
    wait_for(source, sink)
    return 0

if __name__ == '__main__':
    sys.exit(main())
