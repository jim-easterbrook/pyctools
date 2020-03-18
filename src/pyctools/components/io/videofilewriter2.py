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

__all__ = ['VideoFileWriter2']

from contextlib import contextmanager
import os
import subprocess

import numpy

from pyctools.core.config import ConfigEnum, ConfigFloat, ConfigPath
from pyctools.core.frame import Frame, Metadata
from pyctools.core.base import Component
from pyctools.core.types import pt_float


class VideoFileWriter2(Component):
    """Write video files, including "raw" format.

    This component uses FFmpeg_ to write video to a variety of formats.
    Make sure you have installed FFmpeg before attempting to use
    :py:class:`VideoFileWriter2`.

    There are two configuration settings that control the saved file
    format. ``codec`` chooses a codec "family" such as ``'FFV1'`` and
    ``pix_fmt`` chooses the data layout before compression. The
    "container" format, such as ``AVI`` or ``MOV``, is inferred from the
    file name extension. Not all codecs will work with all pixel
    formats, and FFmpeg supports many more pixel formats (and codecs)
    that are available in :py:class:`VideoFileWriter2`. Let me know if
    you have any particular requirements that are not already included.

    The ``raw`` and ``ffv1`` codecs are lossless, but look out for
    unwanted RGB<->YUV conversion or UV resampling. ``H264`` always
    converts to YUV, ``H264rgb`` always converts to RGB.

    The ``input_Y_RGB`` input accepts images with 1 or 3 components as Y
    or RGB. The ``input_UV`` input accepts UV images with 2 components.
    The ``input`` config specifies the expected inputs.

    ===========  ===  ====
    Config
    ===========  ===  ====
    ``path``     str  Path name of file to be written.
    ``input``    str  The input video format. Can be ``'RGB'``, ``'YUV'``, or ``'Y'``.
    ``codec``    str  Codec name. Possible values: {}.
    ``pix_fmt``  str  Pixel format. Possible values: {}.
    ``fps``      int  Video frame rate. Only affects how file is replayed.
    ===========  ===  ====

    .. _FFmpeg: https://www.ffmpeg.org/
    .. _fourcc: https://www.fourcc.org/

    """

    with_outframe_pool = False
    inputs = ['input_Y_RGB', 'input_UV']     #:
    outputs = []

    fourcc = {
        'gray'    : 'Y8',
        'gray16le': 'Y16',
        'rgb24'   : 'BGR[24]',
        'uyvy422' : 'UYVY',
        'yuv422p' : 'YV16',
        }

    codecs = {
        'raw'    : ['-c:v', 'rawvideo'],
        'FFV1'   : ['-c:v', 'ffv1'],
        'H264'   : ['-c:v', 'libx264', '-qp', '0'],
        'H264rgb': ['-c:v', 'libx264rgb', '-qp', '0'],
        }

    pix_fmts = ('rgb24', 'rgb48le', 'uyvy422', 'yuv422p', 'yuv422p10le',
                'gray', 'gray16le')

    __doc__ = __doc__.format(
        ', '.join(["``'" + x + "'``"for x in codecs.keys()]),
        ', '.join(["``'" + x + "'``"for x in pix_fmts]))

    def initialise(self):
        self.config['path'] = ConfigPath(exists=False)
        self.config['input'] = ConfigEnum(choices=('RGB', 'YUV', 'Y'))
        self.config['codec'] = ConfigEnum(choices=(self.codecs.keys()))
        self.config['pix_fmt'] = ConfigEnum(choices=self.pix_fmts)
        self.config['fps'] = ConfigFloat(value=25, min_value=1, decimals=2)

    def on_start(self):
        # start generator to write data
        self.generator = self.file_writer()
        next(self.generator)

    def process_frame(self):
        Y_frame = self.input_buffer['input_Y_RGB'].get()
        UV_frame = self.input_buffer['input_UV'].peek()
        if UV_frame.frame_no >= 0:
            UV_frame = self.input_buffer['input_UV'].get()
        else:
            UV_frame = None
        # send frame(s) to generator
        self.generator.send((Y_frame, UV_frame))

    @contextmanager
    def subprocess(self, *arg, **kw):
        sp = None
        try:
            sp = subprocess.Popen(*arg, **kw)
            yield sp
        finally:
            if sp:
                sp.stdin.flush()
                sp.stdin.close()
                sp.wait()

    def file_writer(self):
        self.update_config()
        path = self.config['path']
        input_ = self.config['input']
        codec = self.config['codec']
        out_fmt = self.config['pix_fmt']
        fps = self.config['fps']
        # if no UV input expected, create a dummy "static" frame
        if input_ != 'YUV':
            self.input_UV(Frame())
        # get first frame
        Y_frame, UV_frame = yield True
        Y_data = Y_frame.as_numpy()
        # check number of components
        ylen, xlen, comps = Y_data.shape
        if UV_frame:
            if comps != 1:
                self.logger.critical('Y input has %d components', comps)
                return
            UV_data = UV_frame.as_numpy()
            UV_ylen, UV_xlen, UV_comps = UV_data.shape
            if UV_comps != 2:
                self.logger.critical('UV input has %d components', UV_comps)
                return
        elif comps not in (1, 3):
            self.logger.critical('Y/RGB input has %d components', comps)
            return
        # choose format to send data to FFmpeg
        bit16 = True
        if UV_frame:
            ss_x = xlen // UV_xlen
            ss_y = ylen // UV_xlen
            if ss_x == 1 and ss_y == 1:
                if out_fmt in ('yuv444p', 'gray'):
                    in_fmt = 'yuv444p'
                    bit16 = False
                else:
                    in_fmt = 'yuv444p16le'
            elif ss_x == 2 and ss_y == 1:
                if out_fmt in ('uyvy422', 'yuv422p', 'gray'):
                    in_fmt = 'yuv422p'
                    bit16 = False
                else:
                    in_fmt = 'yuv422p16le'
            elif ss_x == 2 and ss_y == 2:
                if out_fmt in ('yuv420p', 'gray'):
                    in_fmt = 'yuv420p'
                    bit16 = False
                else:
                    in_fmt = 'yuv420p16le'
        elif comps == 3:
            if out_fmt in ('rgb24', ):
                bit16 = False
                in_fmt = 'bgr24'
            else:
                in_fmt = 'bgr48le'
        else:
            if out_fmt in ('gray', ):
                bit16 = False
                in_fmt = 'gray'
            else:
                in_fmt = 'gray16le'
        if in_fmt != out_fmt:
            self.logger.warning(
                'Converting "%s" to "%s" in FFmpeg', in_fmt, out_fmt)
        # save metadata
        metadata = Metadata().copy(Y_frame.metadata)
        if codec == 'raw':
            # store what's needed to read file
            if out_fmt not in self.fourcc:
                self.logger.critical('Cannot store "%s" in a raw file', out_fmt)
                return
            metadata.set('fourcc', self.fourcc[out_fmt])
            metadata.set('xlen', str(xlen))
            metadata.set('ylen', str(ylen))
        else:
            metadata.set('fourcc', None)
            metadata.set('xlen', None)
            metadata.set('ylen', None)
        if UV_frame:
            metadata.merge_audit({'Y': Y_frame, 'UV': UV_frame})
            in_name = 'multiplex(Y, UV)'
        else:
            in_name = 'data'
        metadata.set_audit(
            self, '{} = {}\n    FFmpeg: {} -> {}\n'.format(
                os.path.basename(path), in_name, in_fmt, out_fmt),
            with_date=True, with_config=self.config)
        metadata.to_file(path)
        # save data
        with self.subprocess(
                ['ffmpeg', '-v', 'error', '-y', '-an',
                 '-f', 'rawvideo', '-s', '{}x{}'.format(xlen, ylen),
                 '-r', '{}'.format(fps), '-pix_fmt', in_fmt, '-i', '-']
                + self.codecs[codec]
                + ['-r', '{}'.format(fps), '-pix_fmt', out_fmt, path],
                stdin=subprocess.PIPE) as sp:
            while True:
                if bit16:
                    Y_data = Y_data.astype(pt_float) * pt_float(256.0)
                    Y_data = Y_data.clip(
                        pt_float(0), pt_float(2**16 - 1)).astype('<u2')
                else:
                    Y_data = Y_frame.as_numpy(dtype=numpy.uint8)
                sp.stdin.write(Y_data.tobytes())
                if in_fmt.startswith('yuv'):
                    UV_data = UV_frame.as_numpy(dtype=pt_float)
                    if UV_data.shape != (UV_ylen, UV_xlen, UV_comps):
                        self.logger.critical('UV dimensions changed')
                        return
                    # add offset to make unsigned byte data
                    UV_data = UV_data + pt_float(128.0)
                    if bit16:
                        UV_data = UV_data * pt_float(256.0)
                        UV_data = UV_data.clip(
                            pt_float(0), pt_float(2**16 - 1)).astype('<u2')
                    else:
                        UV_data = UV_data.clip(
                            pt_float(0), pt_float(255)).astype(numpy.uint8)
                    sp.stdin.write(UV_data[:,:,0].tobytes())
                    sp.stdin.write(UV_data[:,:,1].tobytes())
                # get next frame
                Y_frame, UV_frame = yield True
                Y_data = Y_frame.as_numpy()
                if Y_data.shape != (ylen, xlen, comps):
                    self.logger.critical('Y/RGB dimensions changed')
                    return
