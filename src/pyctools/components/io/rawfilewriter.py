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

__all__ = ['RawFileWriter']

from datetime import datetime
import os

import numpy

from pyctools.core.config import ConfigPath, ConfigEnum
from pyctools.core.frame import Frame, Metadata
from pyctools.core.base import Component
from pyctools.core.types import pt_float


class RawFileWriter(Component):
    """Write "raw" Y, YUV, or RGB files.

    The ``input_Y_RGB`` input accepts images with 1 or 3 components as Y
    or RGB. The ``input_UV`` input accepts UV images with 2 components.
    The ``fourcc`` config specifies how the data is arranged in the
    file. See the fourcc_ website for more detail.

    Note that no RGB<->YUV conversion or resampling is done in this
    component. Use the
    :py:class:`~pyctools.components.colourspace.rgbtoyuv.RGBtoYUV` and
    :py:class:`~pyctools.components.interp.resize.Resize` components to
    do that.

    ===========  ===  ====
    Config
    ===========  ===  ====
    ``path``     str  Path name of file to be written.
    ``fourcc``   str  Pixel format. Possible values: {}.
    ===========  ===  ====

    .. _fourcc: https://www.fourcc.org/

    """

    with_outframe_pool = False
    inputs = ['input_Y_RGB', 'input_UV']     #:
    outputs = []

    single_modes = ('Y8', 'Y16', 'RGB[24]')
    dual_modes = ('UYVY',)

    __doc__ = __doc__.format(
        ', '.join(["``'" + x + "'``"for x in single_modes + dual_modes]))

    def initialise(self):
        self.config['path'] = ConfigPath(exists=False)
        self.config['fourcc'] = ConfigEnum(
            choices=self.single_modes + self.dual_modes)

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

    def file_writer(self):
        self.update_config()
        path = self.config['path']
        fourcc = self.config['fourcc']
        # if no UV input expected, create a dummy "static" frame
        if fourcc in self.single_modes:
            self.input_UV(Frame())
        # get first frame
        Y_frame, UV_frame = yield True
        Y_data = Y_frame.as_numpy()
        ylen, xlen, comps = Y_data.shape
        # save metadata
        metadata = Metadata().copy(Y_frame.metadata)
        metadata.set('fourcc', fourcc)
        metadata.set('xlen', str(xlen))
        metadata.set('ylen', str(ylen))
        if UV_frame:
            audit = 'Y = {\n'
            for line in Y_frame.metadata.get('audit').splitlines():
                audit += '    ' + line + '\n'
            audit += '    }\n'
            audit += 'UV = {\n'
            for line in UV_frame.metadata.get('audit').splitlines():
                audit += '    ' + line + '\n'
            audit += '    }\n'
            audit += '{} = RawFileWriter(Y, UV)\n'.format(os.path.basename(path))
        else:
            audit = metadata.get('audit')
            audit += '{} = RawFileWriter(data)\n'.format(os.path.basename(path))
        audit += self.config.audit_string()
        audit += '    time: {}\n'.format(datetime.now().isoformat())
        metadata.set('audit', audit)
        metadata.to_file(path)
        # save data
        with open(path, 'wb') as raw_file:
            while True:
                # convert to required data type
                if fourcc == 'Y16':
                    # little endian 16-bit unsigned
                    Y_data = Y_data.astype(pt_float) * pt_float(256.0)
                    Y_data = Y_data.clip(
                        pt_float(0), pt_float(2**16 - 1)).astype('<u2')
                else:
                    # 8 bit unsigned
                    Y_data = Y_frame.as_numpy(dtype=numpy.uint8)
                if UV_frame:
                    UV_data = UV_frame.as_numpy(dtype=pt_float)
                    ylenUV, xlenUV, compsUV = UV_data.shape
                    if compsUV != 2:
                        self.logger.critical(
                            'UV input has %d components', compsUV)
                        return
                    # add offset to make unsigned byte data
                    UV_data = UV_data + pt_float(128.0)
                    UV_data = UV_data.clip(
                        pt_float(0), pt_float(255)).astype(numpy.uint8)
                # multiplex data
                if comps == 3 and fourcc == 'RGB[24]':
                    R, G, B = numpy.dsplit(Y_data, 3)
                    mux_data = numpy.dstack((B, G, R))
                elif comps == 1 and fourcc in ('Y16', 'Y8'):
                    mux_data = Y_data
                elif comps == 1 and fourcc == 'UYVY':
                    if (ylenUV, xlenUV) != (ylen, xlen // 2):
                        self.logger.critical(
                            'UV input dims %dx%d do not match Y',
                            ylenUV, xlenUV)
                        return
                    Y0, Y1 = numpy.dsplit(Y_data.reshape(ylen, xlen // 2, 2), 2)
                    U, V = numpy.dsplit(UV_data, 2)
                    mux_data = numpy.dstack((U, Y0, V, Y1))
                else:
                    self.logger.critical(
                        'Cannot save %d comps as %s', comps, fourcc)
                    return
                raw_file.write(mux_data.tobytes())
                # get next frame
                Y_frame, UV_frame = yield True
                Y_data = Y_frame.as_numpy()
                if Y_data.shape != (ylen, xlen, comps):
                    self.logger.critical('Image dimensions changed')
                    return
