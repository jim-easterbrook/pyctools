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

import io
import os

import numpy

from pyctools.core.config import ConfigBool, ConfigEnum, ConfigInt, ConfigPath
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
    or stored in separate planes. The formats are labelled with a short
    string knows as a fourcc_ code. This code needs to be in the
    metadata file with the image dimensions.

    Note that when reading "YUV" formats the U & V outputs are offset by
    128 to restore their range to -128..127 (from the file range of
    0..255). This makes subsequent processing a lot easier.

    The ``zperiod`` config item can be used to adjust the repeat period
    so it is an integer multiple of a chosen number, e.g. 4 frames for a
    PAL encoded sequence. It has no effect if ``looping`` is not
    ``repeat``.

    ===========  ====  ====
    Config
    ===========  ====  ====
    ``path``     str   Path name of file to be read.
    ``looping``  str   Whether to play continuously. Can be ``'off'``, ``'repeat'`` or ``'reverse'``.
    ``noaudit``  bool  Don't output file's "audit trail" metadata.
    ``zperiod``  int   Adjust repeat period to an integer multiple of ``zperiod``.
    ===========  ====  ====

    .. _fourcc: http://www.fourcc.org/

    """

    inputs = []
    outputs = ['output_Y_RGB', 'output_UV']     #:

    def initialise(self):
        self.config['path'] = ConfigPath()
        self.config['looping'] = ConfigEnum(choices=('off', 'repeat', 'reverse'))
        self.config['noaudit'] = ConfigBool()
        self.config['zperiod'] = ConfigInt(min_value=0)

    def on_start(self):
        # create file reader
        self.generator = self.file_reader()

    def process_frame(self):
        Y_frame, UV_frame = next(self.generator)
        self.send('output_Y_RGB', Y_frame)
        if UV_frame:
            self.send('output_UV', UV_frame)

    params = {
        # fourcc    planar ssy ssx bpp
        'RGB[24]': (False, 1,  1,  24),
        'HDYC'   : (False, 1,  2,  16),
        'IYU2'   : (False, 1,  1,  24),
        'UYNV'   : (False, 1,  2,  16),
        'UYVY'   : (False, 1,  2,  16),
        'V422'   : (False, 1,  2,  16),
        'Y16'    : (True,  1,  1,  16),
        'Y422'   : (False, 1,  2,  16),
        'Y8'     : (True,  1,  1,   8),
        'YUNV'   : (False, 1,  2,  16),
        'YUYV'   : (False, 1,  2,  16),
        'YUY2'   : (False, 1,  2,  16),
        'YVYU'   : (False, 1,  2,  16),
        'I420'   : (True,  2,  2,  12),
        'IYUV'   : (True,  2,  2,  12),
        'YV12'   : (True,  2,  2,  12),
        'YV16'   : (True,  1,  2,  16),
        'YVU9'   : (True,  4,  4,   9),
        }

    def file_reader(self):
        # set metadata
        self.update_config()
        path = self.config['path']
        metadata = Metadata().from_file(path)
        fourcc = metadata.get('fourcc')
        xlen, ylen = metadata.image_size()
        # set params according to dimensions and fourcc
        if fourcc not in self.params:
            self.logger.critical("Can't read '%s' files", fourcc)
            return
        planar, ssy, ssx, bpp = self.params[fourcc]
        bytes_per_frame = ylen * xlen * bpp // 8
        zlen = os.path.getsize(path) // bytes_per_frame
        if zlen < 1:
            self.logger.critical("Zero length file %s", path)
            return
        file_frame = 0
        direction = 1
        frame_no = 0
        with io.open(path, 'rb', 0) as raw_file:
            while True:
                self.update_config()
                looping = self.config['looping']
                zperiod = self.config['zperiod']
                frames = zlen
                if zlen > zperiod and zperiod > 1 and looping == 'repeat':
                    frames -= zlen % zperiod
                if file_frame >= frames:
                    if looping == 'off':
                        return
                    elif looping == 'repeat':
                        file_frame = 0
                        raw_file.seek(0)
                    else:
                        file_frame = frames - 2
                        direction = -1
                elif file_frame < 0:
                    if looping == 'off':
                        return
                    file_frame = 1
                    direction = 1
                if direction < 0:
                    raw_file.seek(-2 * bytes_per_frame, io.SEEK_CUR)
                file_frame += direction
                # read frame into 1D array
                raw_data = raw_file.read(bytes_per_frame)
                if fourcc == 'Y16':
                    data = numpy.ndarray(
                        shape=(ylen * xlen,), dtype='<u2', buffer=raw_data)
                    data = data.astype(pt_float) / pt_float(256.0)
                else:
                    data = numpy.ndarray(
                        shape=(bytes_per_frame,), dtype=numpy.uint8,
                        buffer=raw_data)
                # demux data
                Y_frame = self.outframe_pool['output_Y_RGB'].get()
                Y_frame.metadata.copy(metadata)
                Y_frame.frame_no = frame_no
                Y_frame.type = 'Y'
                Y_audit = 'data = {}\n    fourcc: {}\n'
                UV_frame = None
                if fourcc in ('Y16', 'Y8'):
                    Y = data.reshape((ylen, xlen, 1))
                elif fourcc == 'RGB[24]':
                    Y_frame.type = 'RGB'
                    B, G, R = numpy.dsplit(data.reshape((ylen, xlen, 3)), 3)
                    Y = numpy.dstack((R, G, B))
                else:
                    # YUV data
                    Y_audit = 'data = demultiplex({})[Y]\n    fourcc: {}\n'
                    UV_audit = 'data = demultiplex({})[UV]\n    fourcc: {}\n'
                    UV_frame = self.outframe_pool['output_UV'].get()
                    UV_frame.metadata.copy(metadata)
                    UV_frame.set_audit(
                        self, UV_audit.format(os.path.basename(path), fourcc),
                        with_history=not self.config['noaudit'],
                        with_config=self.config)
                    UV_frame.frame_no = frame_no
                    UV_frame.type = 'CbCr'
                    if planar:
                        Y = data[0:xlen * ylen].reshape((ylen, xlen, 1))
                        UV = data[xlen * ylen:].reshape((
                            2, ylen // ssy, xlen // ssx, 1))
                        if fourcc in ('IYUV', 'I420'):
                            # planar format, YUV order
                            U, V = UV[0], UV[1]
                        else:
                            # planar format, YVU order
                            U, V = UV[1], UV[0]
                    elif fourcc == 'IYU2':
                        U, Y, V = numpy.dsplit(data.reshape((ylen, xlen, 3)), 3)
                    else:
                        quad = numpy.dsplit(
                            data.reshape((ylen, xlen // 2, 4)), 4)
                        if fourcc in ('UYVY', 'UYNV', 'Y422', 'HDYC'):
                            # packed format, UYVY order
                            U, Y0, V, Y1 = quad
                        elif fourcc in ('YVYU',):
                            # packed format, YVYU order
                            Y0, V, Y1, U = quad
                        elif fourcc in ('YUYV', 'YUY2', 'YUNV', 'V422'):
                            # packed format, YUYV order
                            Y0, U, Y1, V = quad
                        Y = numpy.dstack((Y0, Y1))
                        Y = Y.reshape((ylen, xlen, 1))
                    UV = numpy.dstack((U, V))
                    # remove offset
                    UV_frame.data = UV.astype(pt_float) - pt_float(128.0)
                Y_frame.set_audit(
                    self, Y_audit.format(os.path.basename(path), fourcc),
                    with_history=not self.config['noaudit'],
                    with_config=self.config)
                Y_frame.data = Y
                yield Y_frame, UV_frame
                frame_no += 1
