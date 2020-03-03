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

__all__ = ['RawFileReader']
__docformat__ = 'restructuredtext en'

from functools import reduce
import io
import os

import numpy

from pyctools.core.config import ConfigPath, ConfigEnum
from pyctools.core.base import Component
from pyctools.core.frame import Metadata
from pyctools.core.types import pt_float


class RawFileReader(Component):
    """Read "raw" YUV or RGB files.

    Video is usually stored in file formats (such as AVI) with a complex
    structure to allow a mix of audio, video and other data. These can
    be read with the
    :py:class:`~pyctools.components.io.videofilereader.VideoFileReader`
    component.

    This component reads simple "raw" files that contain nothing but the
    picture data. Even the image dimensions have to be stored in a
    separate "metadata" file. (Use the :py:mod:`pyctools-setmetadata
    <pyctools.tools.setmetadata>` tool to create or modify the metadata
    file.)

    There are many possible arrangements of data in raw files. For
    example, the colour components can be packed (multiplexed) together
    or stored in separate planes. The formats are labelled with a four
    character code knows as a `fourcc <http://www.fourcc.org/>`_ code.
    This code needs to be in the metadata file with the image
    dimensions.

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

    inputs = []
    outputs = ['output_Y_RGB', 'output_UV']     #:

    def initialise(self):
        self.config['path'] = ConfigPath()
        self.config['looping'] = ConfigEnum(choices=('off', 'repeat', 'reverse'))

    def on_start(self):
        # set metadata
        self.update_config()
        path = self.config['path']
        self.metadata = Metadata().from_file(path)
        audit = self.metadata.get('audit')
        audit += 'data = %s\n' % path
        self.metadata.set('audit', audit)
        # create file reader
        self.frame_no = 0
        self.generator = self.file_reader()

    def process_frame(self):
        Y_data, UV_data = next(self.generator)
        Y_frame = self.outframe_pool['output_Y_RGB'].get()
        Y_frame.metadata.copy(self.metadata)
        Y_frame.frame_no = self.frame_no
        self.frame_no += 1
        Y_frame.data = Y_data
        Y_frame.type = self.Y_type
        self.send('output_Y_RGB', Y_frame)
        if UV_data is not None:
            UV_frame = self.outframe_pool['output_UV'].get()
            UV_frame.initialise(Y_frame)
            UV_frame.data = UV_data
            UV_frame.type = self.UV_type
            self.send('output_UV', UV_frame)

    def file_reader(self):
        self.update_config()
        path = self.config['path']
        fourcc = self.metadata.get('fourcc')
        xlen, ylen = self.metadata.image_size()
        # set bits per pixel and component dimensions
        UV_shape = {
            'I420': (2, ylen // 2, xlen // 2, 1),
            'IYUV': (2, ylen // 2, xlen // 2, 1),
            'YV16': (2, ylen, xlen // 2, 1),
            'YV12': (2, ylen // 2, xlen // 2, 1),
            'YVU9': (2, ylen // 4, xlen // 4, 1),
            }
        bytes_per_frame = ylen * xlen
        if fourcc in ('RGB[24]', 'IYU2'):
            # 3 components
            bytes_per_frame *= 3
        elif fourcc == 'Y16':
            # 16 bit data
            bytes_per_frame *= 2
        elif fourcc == 'Y8':
            # no UV
            pass
        elif fourcc in UV_shape:
            bytes_per_frame += reduce(lambda x, y: x * y, UV_shape[fourcc])
        else:
            # 4:2:2 sampling
            bytes_per_frame += bytes_per_frame // 2
        zlen = os.path.getsize(path) // bytes_per_frame
        if zlen < 1:
            self.logger.critical("Zero length file %s", path)
            return
        # set frame type
        if fourcc in ('RGB[24]',):
            self.Y_type = 'RGB'
        else:
            self.Y_type = 'Y'
            self.UV_type = 'CbCr'
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
                # read frame into 1D array
                raw_data = raw_file.read(bytes_per_frame)
                if fourcc == 'Y16':
                    dtype = '<u2'
                else:
                    dtype = numpy.uint8
                data = numpy.ndarray(
                    shape=(bytes_per_frame,), dtype=dtype, buffer=raw_data)
                # demux data
                if fourcc in ('Y16', 'Y8'):
                    Y_data = data.reshape((ylen, xlen, 1))
                    UV_data = None
                elif fourcc == 'RGB[24]':
                    B, G, R = numpy.dsplit(data.reshape((ylen, xlen, 3)), 3)
                    Y_data = numpy.dstack((R, G, B))
                    UV_data = None
                else:
                    # YUV data
                    if fourcc == 'IYU2':
                        U, Y, V = numpy.dsplit(data.reshape((ylen, xlen, 3)), 3)
                    elif fourcc in ('UYVY', 'UYNV', 'Y422', 'HDYC'):
                        # packed format, UYVY order
                        U, Y0, V, Y1 = numpy.dsplit(
                            data.reshape((ylen, xlen // 2, 4)), 4)
                        Y = numpy.dstack((Y0, Y1))
                    elif fourcc in ('YVYU',):
                        # packed format, YVYU order
                        Y0, V, Y1, U = numpy.dsplit(
                            data.reshape((ylen, xlen // 2, 4)), 4)
                        Y = numpy.dstack((Y0, Y1))
                    elif fourcc in ('YUYV', 'YUY2', 'YUNV', 'V422'):
                        # packed format, YUYV order
                        Y0, U, Y1, V = numpy.dsplit(
                            data.reshape((ylen, xlen // 2, 4)), 4)
                        Y = numpy.dstack((Y0, Y1))
                    elif fourcc in ('IYUV', 'I420'):
                        # planar format, YUV order
                        Y = data[0:xlen * ylen]
                        UV = data[xlen * ylen:].reshape(UV_shape[fourcc])
                        U, V = UV[0], UV[1]
                    elif fourcc in ('YV16', 'YV12', 'YVU9'):
                        # planar format, YVU order
                        Y = data[0:xlen * ylen]
                        UV = data[xlen * ylen:].reshape(UV_shape[fourcc])
                        U, V = UV[1], UV[0]
                    else:
                        self.logger.critical("Can't open %s files", fourcc)
                        return
                    Y_data = Y.reshape((ylen, xlen, 1))
                    UV_data = numpy.dstack((U, V))
                    # remove offset
                    UV_data = UV_data.astype(pt_float) - pt_float(128.0)
                yield Y_data, UV_data
