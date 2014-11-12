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

"""Read conventional video files (mp4, flv, AVI, etc.).

This component uses `FFmpeg <https://www.ffmpeg.org/>`_ to read video
from a wide variety of formats. Make sure you have installed FFmpeg
before attempting to use :py:class:`VideoFileReader`.

===========  ===  ====
Config
===========  ===  ====
``path``     str  Path name of file to be read.
``looping``  str  Whether to play continuously. Can be ``'off'`` or ``'repeat'``.
``type``     str  Output data type. Can be ``'RGB'`` or ``'Y'``.
``16bit``    str  Attempt to get greater precision than normal 8-bit range. Can be ``'off'`` or ``'on'``.
===========  ===  ====

"""

from __future__ import print_function

__all__ = ['VideoFileReader']
__docformat__ = 'restructuredtext en'

from contextlib import contextmanager
import logging
import os
import re
import subprocess
import sys

from guild.actor import *
import numpy

from pyctools.core.config import ConfigPath, ConfigEnum
from pyctools.core.base import Component
from pyctools.core.frame import Metadata

class VideoFileReader(Component):
    inputs = []
    with_outframe_pool = True

    def initialise(self):
        self.frame_no = 0
        self.generator = None
        self.config['path'] = ConfigPath()
        self.config['looping'] = ConfigEnum(('off', 'repeat'), dynamic=True)
        self.config['type'] = ConfigEnum(('RGB', 'Y'))
        self.config['16bit'] = ConfigEnum(('off', 'on'))

    @contextmanager
    def subprocess(self, *arg, **kw):
        try:
            sp = subprocess.Popen(*arg, **kw)
            yield sp
        finally:
            sp.terminate()
            sp.stdout.close()
            sp.stderr.close()
            sp.wait()

    def file_reader(self):
        """Generator process to read file"""
        self.update_config()
        path = self.config['path']
        self.metadata = Metadata().from_file(path)
        audit = self.metadata.get('audit')
        audit += 'data = %s\n' % path
        audit += '    type: %s, 16bit: %s\n' % (
            self.config['type'], self.config['16bit'])
        self.metadata.set('audit', audit)
        # open file to get dimensions
        with self.subprocess(
                ['ffmpeg', '-v', 'info', '-y', '-an', '-vn', '-i', path, '-'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True) as sp:
            for line in sp.stderr.read().splitlines():
                match = re.search('(\d{2,})x(\d{2,})', line)
                if match:
                    xlen, ylen = map(int, match.groups())
                    break
            else:
                self.logger.critical('Failed to open %s', path)
                return
        while True:
            bit16 = self.config['16bit'] != 'off'
            self.frame_type = self.config['type']
            if self.frame_type == 'RGB':
                bps = 3
                pix_fmt = ('rgb24', 'rgb48le')[bit16]
            else:
                bps = 1
                pix_fmt = ('gray', 'gray16le')[bit16]
            bytes_per_line = xlen * ylen * bps
            if bit16:
                bytes_per_line *= 2
            # open file to read data
            with self.subprocess(
                    ['ffmpeg', '-v', 'warning', '-an', '-i', path,
                     '-f', 'image2pipe', '-pix_fmt', pix_fmt,
                     '-c:v', 'rawvideo', '-'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    bufsize=bytes_per_line) as sp:
                while True:
                    raw_data = sp.stdout.read(bytes_per_line)
                    if len(raw_data) < bytes_per_line:
                        break
                    if bit16:
                        image = numpy.fromstring(raw_data, dtype=numpy.uint16)
                        image = image.astype(numpy.float32) / 256.0
                    else:
                        image = numpy.fromstring(raw_data, dtype=numpy.uint8)
                    yield [image.reshape((ylen, xlen, bps))]
            self.update_config()
            if self.frame_no == 0 or self.config['looping'] == 'off':
                return

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
    from PyQt4 import QtGui
    from ..qt.qtdisplay import QtDisplay

    if len(sys.argv) != 2:
        print('usage: %s video_file' % sys.argv[0])
        return 1
    logging.basicConfig(level=logging.DEBUG)
    print('VideoFileReader demonstration')
    QtGui.QApplication.setAttribute(Qt.AA_X11InitThreads)
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
