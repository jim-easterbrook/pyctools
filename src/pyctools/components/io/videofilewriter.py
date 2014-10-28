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

from pyctools.core import Component, ConfigPath, ConfigInt, ConfigEnum

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
        if frame.type == 'RGB':
            if self.bit16:
                pix_fmt = 'rgb48le'
            else:
                pix_fmt = 'rgb24'
        elif frame.type == 'Y':
            if self.bit16:
                pix_fmt = 'gray16le'
            else:
                pix_fmt = 'gray'
        else:
            self.logger.critical('Cannot write %s frame', frame.type)
            self.stop()
            return
        if self.bit16:
            numpy_image = frame.as_numpy(dtype=numpy.uint16, dstack=True)[0]
        else:
            numpy_image = frame.as_numpy(dtype=numpy.uint8, dstack=True)[0]
        if not self.ffmpeg:
            ylen, xlen = numpy_image.shape[:2]
            self.ffmpeg = subprocess.Popen(
                ['ffmpeg', '-v', 'warning', '-y', '-an',
                 '-s', '%dx%d' % (xlen, ylen),
                 '-f', 'rawvideo', '-c:v', 'rawvideo',
                 '-r', '%d' % fps, '-pix_fmt', pix_fmt, '-i', '-',
                 '-r', '%d' % fps] + encoder.split() + [path],
                stdin=subprocess.PIPE)
        self.ffmpeg.stdin.write(numpy_image.tostring())

    def onStop(self):
        super(VideoFileWriter, self).onStop()
        if self.ffmpeg:
            self.ffmpeg.stdin.close()
            self.ffmpeg.wait()
