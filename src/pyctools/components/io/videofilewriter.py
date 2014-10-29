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

"""Video file writer.

Writes conventional video files.

"""

__all__ = ['VideoFileWriter']

import subprocess

from guild.actor import *
import numpy

from pyctools.core import Component, ConfigPath, ConfigInt, ConfigEnum, Metadata

class VideoFileWriter(Component):
    outputs = []

    def __init__(self):
        super(VideoFileWriter, self).__init__()
        self.config['path'] = ConfigPath()
        self.config['encoder'] = ConfigEnum((
            '-c:v ffv1 -pix_fmt bgr0',
            '-c:v ffv1 -pix_fmt gray',
            '-c:v ffv1 -pix_fmt gray16le',
            '-c:v libx264 -pix_fmt yuv444p -qp 0',
            '-c:v libx264 -pix_fmt yuv444p -qp 0 -preset veryslow',
            ))
        self.config['fps'] = ConfigInt(value=25)
        self.config['16bit'] = ConfigEnum(('off', 'on'))
        self.ffmpeg = None
        self.last_frame_type = None

    @actor_method
    def input(self, frame):
        if not frame:
            self.stop()
            return
        if not self.ffmpeg:
            self.update_config()
            path = self.config['path']
            encoder = self.config['encoder']
            fps = self.config['fps']
            self.bit16 = self.config['16bit'] != 'off'
        if self.bit16:
            numpy_image = frame.as_numpy(dtype=numpy.float32, dstack=True)[0]
            numpy_image = numpy_image * 256.0
            numpy_image = numpy_image.clip(0, 2**16 - 1).astype(numpy.uint16)
        else:
            numpy_image = frame.as_numpy(dtype=numpy.uint8, dstack=True)[0]
        ylen, xlen, bpc = numpy_image.shape
        if bpc == 3:
            if frame.type != 'RGB' and frame.type != self.last_frame_type:
                self.logger.warning('Expected RGB input, got %s', frame.type)
            if self.bit16:
                pix_fmt = 'rgb48le'
            else:
                pix_fmt = 'rgb24'
        elif bpc == 1:
            if frame.type != 'Y' and frame.type != self.last_frame_type:
                self.logger.warning('Expected Y input, got %s', frame.type)
            if self.bit16:
                pix_fmt = 'gray16le'
            else:
                pix_fmt = 'gray'
        else:
            self.logger.critical(
                'Cannot write %s frame with %d components', frame.type, bpc)
            self.stop()
            return
        self.last_frame_type = frame.type
        if not self.ffmpeg:
            self.ffmpeg = subprocess.Popen(
                ['ffmpeg', '-v', 'warning', '-y', '-an',
                 '-s', '%dx%d' % (xlen, ylen),
                 '-f', 'rawvideo', '-c:v', 'rawvideo',
                 '-r', '%d' % fps, '-pix_fmt', pix_fmt, '-i', '-',
                 '-r', '%d' % fps] + encoder.split() + [path],
                stdin=subprocess.PIPE)
            md = Metadata().copy(frame.metadata)
            audit = md.get('audit')
            audit += '%s = data\n' % path
            audit += '    encoder: "%s"\n' % (encoder)
            audit += '    16bit: %s\n' % (self.config['16bit'])
            md.set('audit', audit)
            md.to_file(path)
        self.ffmpeg.stdin.write(numpy_image.tostring())

    def onStop(self):
        super(VideoFileWriter, self).onStop()
        if self.ffmpeg:
            self.ffmpeg.stdin.close()
            self.ffmpeg.wait()
