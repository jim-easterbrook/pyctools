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

__all__ = ['RawFileReader']

import io
import logging
import os
import sys

from guild.actor import *
import numpy

from ...core import Metadata, Component, ConfigPath, ConfigEnum

class RawFileReader(Component):
    inputs = []

    def __init__(self):
        super(RawFileReader, self).__init__(with_outframe_pool=True)
        self.config['path'] = ConfigPath()
        self.config['looping'] = ConfigEnum(('off', 'on'), dynamic=True)

    def process_start(self):
        super(RawFileReader, self).process_start()
        path = self.config['path']
        self.file = io.open(path, 'rb', 0)
        self.metadata = Metadata().from_file(path)
        self.fourcc = self.metadata.get('fourcc')
        self.xlen, self.ylen = self.metadata.image_size()
        # set bits per pixel and UV subsampling ratios
        if self.fourcc in ('IYU2', 'BGR[24]', 'RGB[24]'):
            bpp = 24
            self.ssr = ((1, 1), (1, 1), (1, 1))
        elif self.fourcc in ('UYVY', 'UYNV', 'Y422', 'HDYC', 'YVYU', 'YUYV',
                             'YV16', 'YUY2', 'YUNV', 'V422'):
            bpp = 16
            self.ssr = ((1, 1), (2, 1), (2, 1))
        elif self.fourcc in ('IYUV', 'I420', 'YV12'):
            bpp = 12
            self.ssr = ((1, 1), (2, 2), (2, 2))
        elif self.fourcc in ('YVU9',):
            bpp = 9
            self.ssr = ((1, 1), (4, 4), (4, 4))
        else:
            raise RuntimeError("Can't open %s files" % self.fourcc)
        self.bytes_per_frame = (self.xlen * self.ylen * bpp) // 8
        self.zlen = os.path.getsize(path) // self.bytes_per_frame
        if self.zlen < 1:
            raise RuntimeError("Zero length file %s" % path)
        # set raw array slice parameters
        if self.fourcc in ('BGR[24]',):
            self.slice = ((2, None, 3),
                          (1, None, 3),
                          (0, None, 3))
        elif self.fourcc in ('RGB[24]',):
            self.slice = ((0, None, 3),
                          (1, None, 3),
                          (2, None, 3))
        elif self.fourcc in ('IYU2',):
            self.slice = ((1, None, 3),
                          (0, None, 3),
                          (2, None, 3))
        elif self.fourcc in ('UYVY', 'UYNV', 'Y422', 'HDYC'):
            # packed format, UYVY order
            self.slice = ((1, None, 2),
                          (0, None, 4),
                          (2, None, 4))
        elif self.fourcc in ('YVYU',):
            # packed format, YVYU order
            self.slice = ((0, None, 2),
                          (3, None, 4),
                          (1, None, 4))
        elif self.fourcc in ('YUYV', 'YUY2', 'YUNV', 'V422'):
            # packed format, YUYV order
            self.slice = ((0, None, 2),
                          (1, None, 4),
                          (3, None, 4))
        elif self.fourcc in ('IYUV', 'I420'):
            # planar format, YUV order
            Y_size = self.xlen * self.ylen
            UV_size = Y_size // (self.ssr[1][0] * self.ssr[1][1])
            self.slice = ((0,                Y_size,                 1),
                          (Y_size,           Y_size + UV_size,       1),
                          (Y_size + UV_size, Y_size + (UV_size * 2), 1))
        elif self.fourcc in ('YV16', 'YV12', 'YVU9'):
            # planar format, YVU order
            Y_size = self.xlen * self.ylen
            UV_size = Y_size // (self.ssr[1][0] * self.ssr[1][1])
            self.slice = ((0,                Y_size,                 1),
                          (Y_size + UV_size, Y_size + (UV_size * 2), 1),
                          (Y_size,           Y_size + UV_size,       1))
        else:
            raise RuntimeError("Can't open %s files" % self.fourcc)
        # set frame type
        if self.fourcc in ('BGR[24]', 'RGB[24]'):
            self.frame_type = 'RGB'
        else:
            self.frame_type = 'YCbCr'
        self.frame_no = 0

    @actor_method
    def new_out_frame(self, frame):
        if self.config['looping'] == 'on' and (self.frame_no % self.zlen) == 0:
            self.file.seek(0)
        raw_data = self.file.read(self.bytes_per_frame)
        if len(raw_data) < self.bytes_per_frame:
            self.output(None)
            self.stop()
            return
        # convert to numpy arrays
        raw_array = numpy.frombuffer(raw_data, numpy.uint8)
        for idx in range(len(self.slice)):
            start, end, step = self.slice[idx]
            raw_data = raw_array[start:end:step]
            frame.data.append(raw_data.reshape(
                self.ylen // self.ssr[idx][1], self.xlen // self.ssr[idx][0]))
        if self.frame_type != 'YCbCr':
            frame.data = [numpy.dstack(frame.data)]
        frame.type = self.frame_type
        frame.frame_no = self.frame_no
        self.frame_no += 1
        self.output(frame)

    def onStop(self):
        super(RawFileReader, self).onStop()
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
        print('usage: %s yuv_video_file' % sys.argv[0])
        return 1
    logging.basicConfig(level=logging.DEBUG)
    print('RawFileReader demonstration')
    source = RawFileReader()
    config = source.get_config()
    config['path'] = sys.argv[1]
    source.set_config(config)
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
