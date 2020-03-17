#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2020  Pyctools contributors
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

__all__ = ['VideoFileReader2']
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


class VideoFileReader2(Component):
    """Read conventional video files (mp4, flv, AVI, etc.).

    This component uses FFmpeg_ to read video from a wide variety of
    formats. Make sure you have installed FFmpeg before attempting to
    use :py:class:`VideoFileReader2`.

    Unlike :py:class:`~.videofilereader.VideoFileReader` the file data
    is not converted to Y or RGB video format. This may be useful if you
    want to process the YUV data directly, rather than having to convert
    it from RGB to YUV again.

    The ``zperiod`` config item can be used to adjust the repeat period
    so it is an integer multiple of a chosen number, e.g. 4 frames for a
    PAL encoded sequence. It has no effect if ``looping`` is ``off``.

    ===========  ====  ====
    Config
    ===========  ====  ====
    ``path``     str   Path name of file to be read.
    ``looping``  str   Whether to play continuously. Can be ``'off'`` or ``'repeat'``.
    ``noaudit``  bool  Don't output file's "audit trail" metadata.
    ``zperiod``  int   Adjust repeat period to an integer multiple of ``zperiod``.
    ===========  ====  ====

    .. _FFmpeg: https://www.ffmpeg.org/

    """

    inputs = []
    outputs = ['output_Y_RGB', 'output_UV']     #:

    def initialise(self):
        self.config['path'] = ConfigPath()
        self.config['looping'] = ConfigEnum(choices=('off', 'repeat'))
        self.config['noaudit'] = ConfigBool()
        self.config['zperiod'] = ConfigInt(min_value=0)
        self.UV_connected = False

    def on_connect(self, output_name):
        if output_name == 'output_UV':
            self.UV_connected = True

    def on_start(self):
        self.generator = self.file_reader()

    def process_frame(self):
        Y_frame, UV_frame = next(self.generator)
        self.send('output_Y_RGB', Y_frame)
        if UV_frame:
            self.send('output_UV', UV_frame)

    @contextmanager
    def subprocess(self, *arg, **kw):
        try:
            sp = subprocess.Popen(*arg, **kw)
            yield sp
        finally:
            sp.send_signal(signal.SIGINT)
            sp.stdout.close()
            if sp.stderr:
                sp.stderr.close()
            sp.wait()

    def file_reader(self):
        self.update_config()
        path = self.config['path']
        noaudit = self.config['noaudit']
        # get metadata
        Y_metadata = Metadata().from_file(path)
        # probe file with FFmpeg to get dimensions and format
        header = {}
        cmd = ['ffprobe', '-hide_banner', '-loglevel', 'warning',
               '-show_streams', '-select_streams', 'v:0',
               '-print_format', 'json', path]
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        if p.returncode:
            error = error.decode('utf-8')
            error = error.splitlines()[0]
            self.logger.info('ffprobe: %s', error)
        else:
            output = output.decode('utf-8')
            header = json.loads(output)['streams'][0]
            xlen = header['width']
            ylen = header['height']
            if 'nb_frames' in header:
                zlen = int(header['nb_frames'])
            else:
                zlen = header['duration_ts']
            in_fmt = header['pix_fmt']
            input_opts = ['-an']
        if not header:
            # possibly a raw video file
            fourcc = Y_metadata.get('fourcc')
            xlen = Y_metadata.get('xlen')
            ylen = Y_metadata.get('ylen')
            if fourcc and xlen and ylen:
                header = {'pix_fmt': fourcc}
                xlen = int(xlen)
                ylen = int(ylen)
                zlen = None
                # choose FFmpeg input format according to fourcc code
                if fourcc == 'RGB[24]':
                    in_fmt = 'rgb24'
                elif fourcc == 'BGR[24]':
                    in_fmt = 'bgr24'
                elif fourcc in ('HDYC', 'UYNV', 'UYVY', 'Y422'):
                    in_fmt = 'uyvy422'
                elif fourcc == 'Y16':
                    in_fmt = 'gray16le'
                elif fourcc in ('GREY', 'Y800', 'Y8'):
                    in_fmt = 'gray'
                elif fourcc in ('YUNV', 'YUYV', 'YUY2'):
                    in_fmt = 'yuyv422'
                elif fourcc == 'YVYU':
                    in_fmt = 'yvyu422'
                elif fourcc in ('I420', 'IYUV', 'YV12'):
                    in_fmt = 'yuv411p'
                elif fourcc == 'YV16':
                    in_fmt = 'yuv422p'
                else:
                    in_fmt = fourcc
                input_opts = ['-v', 'error', '-f', 'rawvideo',
                              '-s', '{}x{}'.format(xlen, ylen),
                              '-r', '25', '-pix_fmt', in_fmt]
        if not header:
            # unrecognised file
            self.logger.critical('Unrecognised file type %s', path)
            return
        # choose FFmpeg output format according to file's format
        if in_fmt in ('gray16be', 'gray16le'):
            out_fmt, bps = 'gray16le', 16
        elif in_fmt in ('gray', ):
            out_fmt, bps = 'gray', 8
        elif in_fmt in ('rgb48be', 'rgb48le', 'bgr48be', 'bgr48le'):
            out_fmt, bps = 'rgb48le', 48
        elif in_fmt in ('rgb24', 'bgr24', 'gbrp',
                        '0rgb', 'rgb0', '0bgr', 'bgr0'):
            out_fmt, bps = 'rgb24', 24
        elif in_fmt in ('yuv444p', ):
            out_fmt, bps = 'yuv444p', 24
            UV_shape = 2, ylen, xlen, 1
        elif in_fmt in ('yuv422p16be', 'yuv422p16le',
                        'yuv422p14be', 'yuv422p14le',
                        'yuv422p12be', 'yuv422p12le',
                        'yuv422p10be', 'yuv422p10le'):
            out_fmt, bps = 'yuv422p16le', 32
            UV_shape = 2, ylen, xlen // 2, 1
        elif in_fmt in ('yuyv422', 'yuv422p', 'yuvj422p', 'uyvy422', 'yvyu422'):
            out_fmt, bps = 'yuv422p', 16
            UV_shape = 2, ylen, xlen // 2, 1
        elif in_fmt in ('yuv420p', 'yuv411p'):
            out_fmt, bps = 'yuv411p', 12
            UV_shape = 2, ylen // 2, xlen // 2, 1
        else:
            self.logger.critical(
                'Cannot read "%s" pixel format', header['pix_fmt'])
            return
        bytes_per_frame = (xlen * ylen * bps) // 8
        if zlen is None:
            zlen = os.path.getsize(path) // bytes_per_frame
        # get metadata
        Y_metadata = Metadata().from_file(path)
        if out_fmt.startswith('yuv'):
            if not self.UV_connected:
                self.logger.warning('"output_UV" not connected')
            UV_metadata = Metadata().copy(Y_metadata)
            UV_metadata.set_audit(
                self, 'data = {}[UV]\n    FFmpeg: {} -> {}\n'.format(
                    os.path.basename(path), header['pix_fmt'], out_fmt),
                with_history=not noaudit, with_config=self.config)
            Y_audit = 'data = {}[Y]\n'
        else:
            if self.UV_connected:
                self.logger.critical(
                    'No UV output from "%s" format file', header['pix_fmt'])
                return
            Y_audit = 'data = {}\n'
        Y_audit += '    FFmpeg: {} -> {}\n'
        Y_metadata.set_audit(
            self, Y_audit.format(
                os.path.basename(path), header['pix_fmt'], out_fmt),
            with_history=not noaudit, with_config=self.config)
        # read file repeatedly to allow looping
        frame_no = 0
        while True:
            # can change config once per outer loop
            self.update_config()
            zperiod = self.config['zperiod']
            looping = self.config['looping']
            if frame_no > 0 and looping == 'off':
                break
            # set data parameters
            frames = zlen
            if zlen > zperiod and zperiod > 1 and looping != 'off':
                frames -= (frame_no + zlen) % zperiod
            # open file to read data
            cmd = ['ffmpeg', '-v', 'warning'] + input_opts
            cmd += ['-i', path]
            if out_fmt.startswith('yuv'):
                # UV data range from ffmpeg is half what I expect
                # this filter option doubles it
                cmd += ['-filter:v', 'eq=saturation=2']
            cmd += ['-c:v', 'rawvideo', '-pix_fmt', out_fmt,
                    '-f', 'image2pipe', '-']
            with self.subprocess(
                    cmd, stdin=open(os.devnull), stdout=subprocess.PIPE,
                    bufsize=bytes_per_frame) as sp:
                for z in range(frames):
                    try:
                        raw_data = sp.stdout.read(bytes_per_frame)
                    except Exception as ex:
                        self.logger.exception(ex)
                        return
                    if not raw_data:
                        # premature end of file
                        if z == 0:
                            self.logger.critical('No data read from file')
                            return
                        self.logger.warning(
                            'Adjusting zlen from %d to %d', zlen, z)
                        zlen = z - 1
                        break
                    if out_fmt in ('gray16le', 'rgb48le', 'yuv422p16le'):
                        image = numpy.ndarray(
                            shape=(bytes_per_frame // 2,), dtype='<u2',
                            buffer=raw_data)
                        image = image.astype(pt_float) / pt_float(256.0)
                    else:
                        image = numpy.ndarray(
                            shape=(bytes_per_frame,), dtype=numpy.uint8,
                            buffer=raw_data)
                    Y_frame = self.outframe_pool['output_Y_RGB'].get()
                    Y_frame.metadata.copy(Y_metadata)
                    if out_fmt in ('rgb48le', 'rgb24'):
                        Y_frame.type = 'RGB'
                    else:
                        Y_frame.type = 'Y'
                    Y_frame.frame_no = frame_no
                    if out_fmt.startswith('yuv'):
                        UV_frame = self.outframe_pool['output_UV'].get()
                        UV_frame.metadata.copy(UV_metadata)
                        UV_frame.type = 'CbCr'
                        UV_frame.frame_no = frame_no
                        Y = image[0:xlen * ylen]
                        UV = image[xlen * ylen:]
                        Y_frame.data = Y.reshape((ylen, xlen, 1))
                        UV = UV.reshape(UV_shape)
                        UV = numpy.dstack((UV[0], UV[1]))
                        # remove offset
                        UV_frame.data = UV.astype(pt_float) - pt_float(128.0)
                    else:
                        UV_frame = None
                        Y_frame.data = image.reshape((ylen, xlen, -1))
                    yield Y_frame, UV_frame
                    frame_no += 1
