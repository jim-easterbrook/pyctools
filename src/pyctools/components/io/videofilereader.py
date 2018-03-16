#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-18  Pyctools contributors
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

from __future__ import print_function

__all__ = ['VideoFileReader']
__docformat__ = 'restructuredtext en'

from contextlib import contextmanager
import logging
import os
import re
import signal
import subprocess
import sys

import numpy

from pyctools.core.config import ConfigBool, ConfigPath, ConfigEnum
from pyctools.core.base import Component
from pyctools.core.frame import Metadata
from pyctools.core.types import pt_float

class VideoFileReader(Component):
    """Read conventional video files (mp4, flv, AVI, etc.).

    This component uses `FFmpeg <https://www.ffmpeg.org/>`_ to read
    video from a wide variety of formats. Make sure you have installed
    FFmpeg before attempting to use :py:class:`VideoFileReader`.

    ===========  ====  ====
    Config
    ===========  ====  ====
    ``path``     str   Path name of file to be read.
    ``looping``  str   Whether to play continuously. Can be ``'off'`` or ``'repeat'``.
    ``type``     str   Output data type. Can be ``'RGB'`` or ``'Y'``.
    ``16bit``    bool  Attempt to get greater precision than normal 8-bit range.
    ===========  ====  ====

    """

    inputs = []

    def initialise(self):
        self.frame_no = 0
        self.generator = None
        self.config['path'] = ConfigPath()
        self.config['looping'] = ConfigEnum(choices=('off', 'repeat'))
        self.config['type'] = ConfigEnum(choices=('RGB', 'Y'))
        self.config['16bit'] = ConfigBool()

    @contextmanager
    def subprocess(self, *arg, **kw):
        try:
            sp = subprocess.Popen(*arg, **kw)
            yield sp
        finally:
            sp.send_signal(signal.SIGINT)
            sp.stdout.close()
            sp.stderr.close()
            sp.wait()

    def file_reader(self):
        """Generator process to read file"""
        self.update_config()
        path = self.config['path']
        # open file to get dimensions
        with self.subprocess(
                ['ffmpeg', '-v', 'info', '-y', '-an', '-vn', '-i', path, '-'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=open(os.devnull), universal_newlines=True) as sp:
            for line in sp.stderr.read().splitlines():
                match = re.search('(\d{2,})x(\d{2,})', line)
                if match:
                    xlen, ylen = map(int, match.groups())
                    break
            else:
                self.logger.critical('Failed to open %s', path)
                return
        # read file repeatedly to allow looping
        while True:
            # can change config once per outer loop
            self.update_config()
            bit16 = self.config['16bit']
            self.frame_type = self.config['type']
            self.metadata = Metadata().from_file(path)
            audit = self.metadata.get('audit')
            audit += 'data = %s\n' % path
            audit += '    type: %s, 16bit: %s\n' % (self.frame_type, bit16)
            self.metadata.set('audit', audit)
            bps = {'RGB': 3, 'Y': 1}[self.frame_type]
            pix_fmt = {'RGB': ('rgb24', 'rgb48le'),
                       'Y':   ('gray', 'gray16le')}[self.frame_type][bit16]
            bytes_per_line = xlen * ylen * bps
            if bit16:
                bytes_per_line *= 2
            # open file to read data
            with self.subprocess(
                    ['ffmpeg', '-v', 'warning', '-an', '-i', path,
                     '-f', 'image2pipe', '-pix_fmt', pix_fmt,
                     '-c:v', 'rawvideo', '-'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    stdin=open(os.devnull), bufsize=bytes_per_line) as sp:
                while True:
                    try:
                        raw_data = sp.stdout.read(bytes_per_line)
                    except Exception as ex:
                        self.logger.exception(ex)
                        return
                    if len(raw_data) < bytes_per_line:
                        break
                    if bit16:
                        image = numpy.fromstring(raw_data, dtype=numpy.uint16)
                        image = image.astype(pt_float) / pt_float(256.0)
                    else:
                        image = numpy.fromstring(raw_data, dtype=numpy.uint8)
                    yield image.reshape((ylen, xlen, bps))
            self.update_config()
            if self.frame_no == 0 or self.config['looping'] == 'off':
                return

    def process_frame(self):
        frame = self.outframe_pool['output'].get()
        if not self.generator:
            self.generator = self.file_reader()
        try:
            frame.data = next(self.generator)
        except StopIteration:
            self.stop()
            return
        frame.type = self.frame_type
        frame.frame_no = self.frame_no
        self.frame_no += 1
        frame.metadata.copy(self.metadata)
        self.send('output', frame)
