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

"""Video file reader.

Reads conventional video files (mp4, flv, etc. depends on ffmpeg).

"""

from __future__ import print_function

__all__ = ['VideoFileReader']

import logging
import os
import re
import subprocess
import sys

from guild.actor import *
import numpy

from pyctools.core import Metadata, Component, ConfigPath, ConfigEnum

class VideoFileReader(Component):
    inputs = []

    def __init__(self):
        super(VideoFileReader, self).__init__(with_outframe_pool=True)
        self.ffmpeg = None
        self.config['path'] = ConfigPath()
        self.config['looping'] = ConfigEnum(('off', 'repeat'), dynamic=True)
        self.config['type'] = ConfigEnum(('RGB', 'Y'))
        self.config['16bit'] = ConfigEnum(('off', 'on'))

    def process_start(self):
        super(VideoFileReader, self).process_start()
        self.update_config()
        path = self.config['path']
        # open file to get dimensions
        self.ffmpeg = subprocess.Popen(
            ['ffmpeg', '-v', 'info', '-y', '-an', '-vn', '-i', path, '-'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True)
        for line in self.ffmpeg.stderr.read().splitlines():
            match = re.search('(\d{2,})x(\d{2,})', line)
            if match:
                self.xlen, self.ylen = map(int, match.groups())
                break
        else:
            self.logger.critical('Failed to open %s', path)
            self.output(None)
            self.stop()
            return
        self.ffmpeg.stderr.flush()
        self.open_file()
        self.metadata = Metadata().from_file(path)
        audit = self.metadata.get('audit')
        audit += 'data = %s\n' % path
        audit += '    type: %s, 16bit: %s\n' % (
            self.config['type'], self.config['16bit'])
        self.metadata.set('audit', audit)
        self.frame_no = 0

    def close_file(self):
        if self.ffmpeg:
            self.ffmpeg.terminate()
            self.ffmpeg.stdout.flush()
            self.ffmpeg = None

    def open_file(self):
        self.close_file()
        path = self.config['path']
        self.bit16 = self.config['16bit'] != 'off'
        self.frame_type = self.config['type']
        if self.frame_type == 'RGB':
            self.bps = 3
            if self.bit16:
                pix_fmt = 'rgb48le'
            else:
                pix_fmt = 'rgb24'
        else:
            self.bps = 1
            if self.bit16:
                pix_fmt = 'gray16le'
            else:
                pix_fmt = 'gray'
        self.bytes_per_line = self.xlen * self.ylen * self.bps
        if self.bit16:
            self.bytes_per_line *= 2
        # open file to read data
        self.ffmpeg = subprocess.Popen(
            ['ffmpeg', '-v', 'warning', '-an', '-i', path,
             '-f', 'image2pipe', '-pix_fmt', pix_fmt,
             '-c:v', 'rawvideo', '-'],
            stdout=subprocess.PIPE, bufsize=self.bytes_per_line)

    @actor_method
    def new_out_frame(self, frame):
        self.update_config()
        while True:
            raw_data = self.ffmpeg.stdout.read(self.bytes_per_line)
            if len(raw_data) >= self.bytes_per_line:
                break
            self.close_file()
            if self.frame_no == 0 or self.config['looping'] == 'off':
                self.output(None)
                self.stop()
                return
            self.open_file()
        if self.bit16:
            image = numpy.fromstring(raw_data, dtype=numpy.uint16)
            image = image.astype(numpy.float32) / 256.0
        else:
            image = numpy.fromstring(raw_data, dtype=numpy.uint8)
        frame.data = [image.reshape((self.ylen, self.xlen, self.bps))]
        frame.type = self.frame_type
        frame.frame_no = self.frame_no
        self.frame_no += 1
        frame.metadata.copy(self.metadata)
        self.output(frame)

    def onStop(self):
        super(VideoFileReader, self).onStop()
        self.close_file()

def main():
    from PyQt4 import QtGui
    from ..qt.qtdisplay import QtDisplay

    if len(sys.argv) != 2:
        print('usage: %s video_file' % sys.argv[0])
        return 1
    logging.basicConfig(level=logging.DEBUG)
    print('VideoFileReader demonstration')
    app = QtGui.QApplication([])
    source = VideoFileReader()
    config = source.get_config()
    config['path'] = sys.argv[1]
    config['looping'] = 'repeat'
    source.set_config(config)
    sink = QtDisplay()
    pipeline(source, sink)
    start(source, sink)
    try:
        app.exec_()
    finally:
        stop(source, sink)
        wait_for(source, sink)
    return 0

if __name__ == '__main__':
    sys.exit(main())
