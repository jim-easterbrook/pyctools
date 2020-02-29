#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-20  Pyctools contributors
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
import json
import logging
import os
import re
import signal
import subprocess
import sys

import numpy

from pyctools.core.config import ConfigBool, ConfigEnum, ConfigInt, ConfigPath
from pyctools.core.base import Component
from pyctools.core.frame import Metadata
from pyctools.core.types import pt_float


class VideoFileReader(Component):
    """Read conventional video files (mp4, flv, AVI, etc.).

    This component uses FFmpeg_ to read video from a wide variety of
    formats. Make sure you have installed FFmpeg before attempting to
    use :py:class:`VideoFileReader`.

    The ``zperiod`` config item can be used to adjust the repeat period
    so it is an integer multiple of a chosen number, e.g. 4 frames for a
    PAL encoded sequence. It has no effect if ``looping`` is ``off``.

    ===========  ====  ====
    Config
    ===========  ====  ====
    ``path``     str   Path name of file to be read.
    ``looping``  str   Whether to play continuously. Can be ``'off'`` or ``'repeat'``.
    ``type``     str   Output data type. Can be ``'RGB'`` or ``'Y'``.
    ``16bit``    bool  Attempt to get greater precision than normal 8-bit range.
    ``noaudit``  bool  Don't output file's "audit trail" metadata.
    ``zperiod``  int   Adjust repeat period to an integer multiple of ``zperiod``.
    ===========  ====  ====

    .. _FFmpeg: https://www.ffmpeg.org/

    """

    inputs = []

    def initialise(self):
        self.config['path'] = ConfigPath()
        self.config['looping'] = ConfigEnum(choices=('off', 'repeat'))
        self.config['type'] = ConfigEnum(choices=('RGB', 'Y'))
        self.config['16bit'] = ConfigBool()
        self.config['noaudit'] = ConfigBool()
        self.config['zperiod'] = ConfigInt(min_value=0)

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
        # probe file to get dimensions
        cmd = ['ffprobe', '-hide_banner', '-loglevel', 'warning',
               '-show_streams', '-select_streams', 'v:0',
               '-print_format', 'json', path]
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        if p.returncode:
            error = error.decode('utf-8')
            error = error.splitlines()[0]
            self.logger.critical('ffprobe: %s', error)
            return
        output = output.decode('utf-8')
        header = json.loads(output)['streams'][0]
        xlen = header['width']
        ylen = header['height']
        zlen = header['duration_ts']
        # read file repeatedly to allow looping
        frame_no = 0
        while True:
            # can change config once per outer loop
            self.update_config()
            bit16 = self.config['16bit']
            self.frame_type = self.config['type']
            zperiod = self.config['zperiod']
            looping = self.config['looping']
            if frame_no > 0 and looping == 'off':
                break
            noaudit = self.config['noaudit']
            # update metadata
            self.metadata = Metadata().from_file(path)
            if noaudit:
                audit = ''
            else:
                audit = self.metadata.get('audit')
            audit += 'data = VideoFileReader({})\n'.format(
                os.path.basename(path))
            audit += self.config.audit_string()
            self.metadata.set('audit', audit)
            # set data parameters
            bps = {'RGB': 3, 'Y': 1}[self.frame_type]
            pix_fmt = {'RGB': ('rgb24', 'rgb48le'),
                       'Y':   ('gray', 'gray16le')}[self.frame_type][bit16]
            bytes_per_frame = xlen * ylen * bps
            if bit16:
                bytes_per_frame *= 2
            frames = zlen
            if zlen > zperiod and zperiod > 1 and looping != 'off':
                frames -= (frame_no + zlen) % zperiod
            # open file to read data
            with self.subprocess(
                    ['ffmpeg', '-v', 'warning', '-an', '-i', path,
                     '-f', 'image2pipe', '-pix_fmt', pix_fmt,
                     '-c:v', 'rawvideo', '-'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    stdin=open(os.devnull), bufsize=bytes_per_frame) as sp:
                for z in range(frames):
                    try:
                        raw_data = sp.stdout.read(bytes_per_frame)
                    except Exception as ex:
                        self.logger.exception(ex)
                        return
                    if bit16:
                        image = numpy.fromstring(raw_data, dtype=numpy.uint16)
                        image = image.astype(pt_float) / pt_float(256.0)
                    else:
                        image = numpy.fromstring(raw_data, dtype=numpy.uint8)
                    yield frame_no, image.reshape((ylen, xlen, bps))
                    frame_no += 1

    def on_start(self):
        self.generator = self.file_reader()

    def process_frame(self):
        frame = self.outframe_pool['output'].get()
        frame.frame_no, frame.data = next(self.generator)
        frame.type = self.frame_type
        frame.metadata.copy(self.metadata)
        self.send('output', frame)
