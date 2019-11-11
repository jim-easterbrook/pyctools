#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-19  Pyctools contributors
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
        try:
            Y_data, UV_data = next(self.generator)
        except StopIteration:
            self.stop()
            return
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
        """Generator process to read file"""
        self.update_config()
        path = self.config['path']
        fourcc = self.metadata.get('fourcc')
        xlen, ylen = self.metadata.image_size()
        # set bits per pixel and component dimensions
        if fourcc in ('BGR[24]',):
            bpp = 24
            Y_shape = (ylen, xlen)
        elif fourcc in ('RGB[24]',):
            bpp = 24
            Y_shape = (ylen, xlen, 3)
        elif fourcc in ('IYU2',):
            bpp = 24
            Y_shape = (ylen, xlen, 1)
            UV_shape = (ylen, xlen)
        elif fourcc in ('UYVY', 'UYNV', 'Y422', 'HDYC', 'YVYU', 'YUYV',
                        'YV16', 'YUY2', 'YUNV', 'V422'):
            bpp = 16
            Y_shape = (ylen, xlen, 1)
            UV_shape = (ylen, xlen // 2)
        elif fourcc in ('IYUV', 'I420', 'YV12'):
            bpp = 12
            Y_shape = (ylen, xlen, 1)
            UV_shape = (ylen // 2, xlen // 2)
        elif fourcc in ('YVU9',):
            bpp = 9
            Y_shape = (ylen, xlen, 1)
            UV_shape = (ylen // 4, xlen // 4)
        else:
            self.logger.critical("Can't open %s files", fourcc)
            return
        bytes_per_frame = (xlen * ylen * bpp) // 8
        zlen = os.path.getsize(path) // bytes_per_frame
        if zlen < 1:
            self.logger.critical("Zero length file %s", path)
            return
        # set raw array slice parameters
        if fourcc in ('BGR[24]',):
            Y_slice = ((2, None, 3), (1, None, 3), (0, None, 3))
            UV_slice = None
        elif fourcc in ('RGB[24]',):
            Y_slice = ((0, None, 1),)
            UV_slice = None
        elif fourcc in ('IYU2',):
            Y_slice = ((1, None, 3),)
            UV_slice = ((0, None, 3), (2, None, 3))
        elif fourcc in ('UYVY', 'UYNV', 'Y422', 'HDYC'):
            # packed format, UYVY order
            Y_slice = ((1, None, 2),)
            UV_slice = ((0, None, 4), (2, None, 4))
        elif fourcc in ('YVYU',):
            # packed format, YVYU order
            Y_slice = ((0, None, 2),)
            UV_slice = ((3, None, 4), (1, None, 4))
        elif fourcc in ('YUYV', 'YUY2', 'YUNV', 'V422'):
            # packed format, YUYV order
            Y_slice = ((0, None, 2),)
            UV_slice = ((1, None, 4), (3, None, 4))
        elif fourcc in ('IYUV', 'I420'):
            # planar format, YUV order
            Y_size = xlen * ylen
            UV_size = UV_shape[0] * UV_shape[1]
            Y_slice = ((0,                Y_size,                 1),)
            UV_slice = ((Y_size,           Y_size + UV_size,       1),
                        (Y_size + UV_size, Y_size + (UV_size * 2), 1))
        elif fourcc in ('YV16', 'YV12', 'YVU9'):
            # planar format, YVU order
            Y_size = xlen * ylen
            UV_size = UV_shape[0] * UV_shape[1]
            Y_slice = ((0,                Y_size,                 1),)
            UV_slice = ((Y_size + UV_size, Y_size + (UV_size * 2), 1),
                        (Y_size,           Y_size + UV_size,       1))
        else:
            self.logger.critical("Can't open %s files", fourcc)
            return
        # set frame type
        if fourcc in ('BGR[24]', 'RGB[24]'):
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
                raw_data = raw_file.read(bytes_per_frame)
                # convert to numpy arrays
                raw_array = numpy.frombuffer(raw_data, numpy.uint8)
                Y_data = []
                for start, end, step in Y_slice:
                    raw_data = raw_array[start:end:step]
                    Y_data.append(raw_data.reshape(Y_shape))
                if len(Y_data) > 1:
                    Y_data = numpy.dstack(Y_data)
                else:
                    Y_data = Y_data[0]
                if UV_slice:
                    UV_data = []
                    for start, end, step in UV_slice:
                        raw_data = raw_array[start:end:step]
                        UV_data.append(raw_data.reshape(UV_shape))
                    UV_data = numpy.dstack(UV_data)
                    # remove offset
                    UV_data = UV_data.astype(pt_float) - pt_float(128.0)
                else:
                    UV_data = None
                yield Y_data, UV_data
