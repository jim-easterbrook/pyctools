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

"""Read "raw" YUV or RGB files.

Video is usually stored in file formats (such as AVI) with a complex
structure to allow a mix of audio, video and other data. These can be
read with the :py:mod:`VideoFileReader
<pyctools.components.io.videofilereader>` component.

This component reads simple "raw" files that contain nothing but the
picture data. Even the image dimensions have to be stored in a
separate "metadata" file. (Use the :py:mod:`pyctools-setmetadata
<pyctools.tools.setmetadata>` tool to create or modify the metadata
file.)

There are many possible arrangements of data in raw files. For
example, the colour components can be packed (multiplexed) together or
stored in separate planes. The formats are labelled with a four
character code knows as a `fourcc <http://www.fourcc.org/>`_ code.
This code needs to be in the metadata file with the image dimensions.

Note that when reading "YUV" formats the U & V outputs are offset by
128 to restore their range to -128..127 (from the file range of
0..255). This makes subsequent processing a lot easier.

===========  ===  ====
Config
===========  ===  ====
``path``     str  Path name of file to be read.
``looping``  str  Whether to play continuously. Can be ``'off'``, ``'repeat'`` or ``'reverse'``.
===========  ===  ====

"""

from __future__ import print_function

__all__ = ['RawFileReader']
__docformat__ = 'restructuredtext en'

import io
import logging
import os
import sys

from guild.actor import *
import numpy

from pyctools.core.config import ConfigPath, ConfigEnum
from pyctools.core.base import Component
from pyctools.core.frame import Metadata

class RawFileReader(Component):
    inputs = []
    with_outframe_pool = True

    def initialise(self):
        self.frame_no = 0
        self.generator = None
        self.config['path'] = ConfigPath()
        self.config['looping'] = ConfigEnum(
            ('off', 'repeat', 'reverse'), dynamic=True)

    def file_reader(self):
        """Generator process to read file"""
        self.update_config()
        path = self.config['path']
        self.metadata = Metadata().from_file(path)
        audit = self.metadata.get('audit')
        audit += 'data = %s\n' % path
        self.metadata.set('audit', audit)
        fourcc = self.metadata.get('fourcc')
        xlen, ylen = self.metadata.image_size()
        # set bits per pixel and component dimensions
        if fourcc in ('IYU2', 'BGR[24]'):
            bpp = 24
            shape = ((ylen, xlen), (ylen, xlen), (ylen, xlen))
        elif fourcc in ('RGB[24]',):
            bpp = 24
            shape = ((ylen, xlen, 3),)
        elif fourcc in ('UYVY', 'UYNV', 'Y422', 'HDYC', 'YVYU', 'YUYV',
                        'YV16', 'YUY2', 'YUNV', 'V422'):
            bpp = 16
            shape = ((ylen, xlen), (ylen, xlen // 2), (ylen, xlen // 2))
        elif fourcc in ('IYUV', 'I420', 'YV12'):
            bpp = 12
            shape = ((ylen, xlen), (ylen // 2, xlen // 2), (ylen // 2, xlen // 2))
        elif fourcc in ('YVU9',):
            bpp = 9
            shape = ((ylen, xlen), (ylen // 4, xlen // 4), (ylen // 4, xlen // 4))
        else:
            self.logger.critical("Can't open %s files", fourcc)
            return
        bytes_per_frame = (xlen * ylen * bpp) // 8
        zlen = os.path.getsize(path) // bytes_per_frame
        if zlen < 1:
            self.logger.critical("Zero length file %s", path)
            return
        # set raw array slice parameters
        if fourcc in ('BGR[24]',):
            data_slice = ((2, None, 3), (1, None, 3), (0, None, 3))
        elif fourcc in ('RGB[24]',):
            data_slice = ((0, None, 1),)
        elif fourcc in ('IYU2',):
            data_slice = ((1, None, 3), (0, None, 3), (2, None, 3))
        elif fourcc in ('UYVY', 'UYNV', 'Y422', 'HDYC'):
            # packed format, UYVY order
            data_slice = ((1, None, 2), (0, None, 4), (2, None, 4))
        elif fourcc in ('YVYU',):
            # packed format, YVYU order
            data_slice = ((0, None, 2), (3, None, 4), (1, None, 4))
        elif fourcc in ('YUYV', 'YUY2', 'YUNV', 'V422'):
            # packed format, YUYV order
            data_slice = ((0, None, 2), (1, None, 4), (3, None, 4))
        elif fourcc in ('IYUV', 'I420'):
            # planar format, YUV order
            Y_size = xlen * ylen
            UV_size = shape[1][0] * shape[1][1]
            data_slice = ((0,                Y_size,                 1),
                          (Y_size,           Y_size + UV_size,       1),
                          (Y_size + UV_size, Y_size + (UV_size * 2), 1))
        elif fourcc in ('YV16', 'YV12', 'YVU9'):
            # planar format, YVU order
            Y_size = xlen * ylen
            UV_size = shape[1][0] * shape[1][1]
            data_slice = ((0,                Y_size,                 1),
                          (Y_size + UV_size, Y_size + (UV_size * 2), 1),
                          (Y_size,           Y_size + UV_size,       1))
        else:
            self.logger.critical("Can't open %s files", fourcc)
            return
        # set frame type
        if fourcc in ('BGR[24]', 'RGB[24]'):
            self.frame_type = 'RGB'
        else:
            self.frame_type = 'YCbCr'
        file_frame = 0
        direction = 1
        with io.open(path, 'rb', 0) as raw_file:
            while True:
                self.update_config()
                if file_frame >= zlen:
                    if self.config['looping'] == 'off':
                        break
                    elif self.config['looping'] == 'repeat':
                        file_frame = 0
                        raw_file.seek(0)
                    else:
                        file_frame = zlen - 2
                        direction = -1
                elif file_frame < 0:
                    file_frame = 1
                    direction = 1
                if direction != 1:
                    raw_file.seek((direction - 1) * bytes_per_frame, io.SEEK_CUR)
                file_frame += direction
                raw_data = raw_file.read(bytes_per_frame)
                # convert to numpy arrays
                data = []
                raw_array = numpy.frombuffer(raw_data, numpy.uint8)
                for slc, shp in zip(data_slice, shape):
                    start, end, step = slc
                    raw_data = raw_array[start:end:step]
                    data.append(raw_data.reshape(shp))
                if self.frame_type == 'YCbCr':
                    # remove offset
                    data[1] = data[1].astype(numpy.float32) - 128.0
                    data[2] = data[2].astype(numpy.float32) - 128.0
                yield data

    @actor_method
    def new_out_frame(self, frame):
        """new_out_frame(frame)

        """
        if not self.generator:
            self.generator = self.file_reader()
        try:
            frame.data = next(self.generator)
        except StopIteration:
            self.output(None)
            self.stop()
            return
        frame.type = self.frame_type
        frame.frame_no = self.frame_no
        self.frame_no += 1
        frame.metadata.copy(self.metadata)
        self.output(frame)

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
