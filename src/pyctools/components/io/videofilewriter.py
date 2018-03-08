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

__all__ = ['VideoFileWriter']

from contextlib import contextmanager
import subprocess

import numpy

from pyctools.core.config import ConfigBool, ConfigPath, ConfigInt, ConfigEnum
from pyctools.core.frame import Metadata
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float

class VideoFileWriter(Transformer):
    """Write video files.

    This component uses `FFmpeg <https://www.ffmpeg.org/>`_ to write
    video to a variety of formats. Make sure you have installed FFmpeg
    before attempting to use :py:class:`VideoFileWriter`.

    The trickiest part of configuring :py:class:`VideoFileWriter` is
    setting ``encoder``. Combinations I've found to work on my machine
    include the following:

    * ``'-c:v ffv1 -pix_fmt bgr0'`` -- FFV1 lossless encoder, 8-bit colour
    * ``'-c:v ffv1 -pix_fmt gray'`` -- FFV1, 8-bit luminance
    * ``'-c:v ffv1 -pix_fmt gray16le'`` FFV1, 16-bit luminance
    * ``'-c:v libx264 -pix_fmt yuv444p -qp 0'`` -- "lossless" H264
    * ``'-c:v libx264 -pix_fmt yuv444p -qp 0 -preset veryslow'`` -- same as above?

    I'd be interested to hear of any other good combinations. Email me
    at the address shown below.

    ===========  ====  ====
    Config
    ===========  ====  ====
    ``path``     str   Path name of file to be created.
    ``encoder``  str   A string of ``ffmpeg`` options.
    ``fps``      int   Video frame rate. Only affects how file is replayed.
    ``16bit``    bool  Attempt to write precision than normal 8-bit range.
    ===========  ====  ====

    """

    def initialise(self):
        self.generator = None
        self.config['path'] = ConfigPath(exists=False)
        self.config['encoder'] = ConfigEnum(choices=(
            '-c:v ffv1 -pix_fmt bgr0',
            '-c:v ffv1 -pix_fmt gray',
            '-c:v ffv1 -pix_fmt gray16le',
            '-c:v libx264 -pix_fmt yuv444p -qp 0',
            '-c:v libx264 -pix_fmt yuv444p -qp 0 -preset veryslow',
            ), extendable=True)
        self.config['fps'] = ConfigInt(value=25)
        self.config['16bit'] = ConfigBool()

    @contextmanager
    def subprocess(self, *arg, **kw):
        try:
            sp = subprocess.Popen(*arg, **kw)
            yield sp
        finally:
            sp.stdin.flush()
            sp.stdin.close()
            sp.wait()

    def file_writer(self, in_frame):
        """Generator process to write file"""
        self.update_config()
        path = self.config['path']
        encoder = self.config['encoder']
        fps = self.config['fps']
        bit16 = self.config['16bit']
        numpy_image = in_frame.as_numpy()
        ylen, xlen, bpc = numpy_image.shape
        if bpc == 3:
            if in_frame.type != 'RGB':
                self.logger.warning('Expected RGB input, got %s', in_frame.type)
            pix_fmt = ('rgb24', 'rgb48le')[bit16]
        elif bpc == 1:
            if in_frame.type != 'Y':
                self.logger.warning('Expected Y input, got %s', in_frame.type)
            pix_fmt = ('gray', 'gray16le')[bit16]
        else:
            self.logger.critical(
                'Cannot write %s frame with %d components', in_frame.type, bpc)
            return
        md = Metadata().copy(in_frame.metadata)
        audit = md.get('audit')
        audit += '%s = data\n' % path
        audit += '    encoder: "%s"\n' % (encoder)
        audit += '    16bit: %s\n' % (self.config['16bit'])
        md.set('audit', audit)
        md.to_file(path)
        with self.subprocess(
                ['ffmpeg', '-v', 'warning', '-y', '-an',
                 '-s', '%dx%d' % (xlen, ylen),
                 '-f', 'rawvideo', '-c:v', 'rawvideo',
                 '-r', '%d' % fps, '-pix_fmt', pix_fmt, '-i', '-',
                 '-r', '%d' % fps] + encoder.split() + [path],
                stdin=subprocess.PIPE) as sp:
            while True:
                in_frame = yield True
                if not in_frame:
                    break
                if bit16:
                    numpy_image = in_frame.as_numpy(dtype=pt_float)
                    numpy_image = numpy_image * pt_float(256.0)
                    numpy_image = numpy_image.clip(
                        pt_float(0), pt_float(2**16 - 1)).astype(numpy.uint16)
                else:
                    numpy_image = in_frame.as_numpy(dtype=numpy.uint8)
                sp.stdin.write(numpy_image.tostring())
                del in_frame

    def transform(self, in_frame, out_frame):
        if not self.generator:
            self.generator = self.file_writer(in_frame)
            try:
                self.generator.send(None)
            except StopIteration:
                return False
        try:
            self.generator.send(in_frame)
        except Exception as ex:
            self.logger.exception(ex)
            return False
        return True

    def on_stop(self):
        if self.generator:
            try:
                self.generator.send(None)
            except StopIteration:
                pass
