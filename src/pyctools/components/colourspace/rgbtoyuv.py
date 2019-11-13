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

__all__ = ['RGBtoYUV']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigEnum
from pyctools.core.base import Component
from pyctools.core.types import pt_float
from .matrices import Matrices


class RGBtoYUV(Component):
    """RGB to YUV (YCbCr) converter.

    Convert RGB frames to "YUV" (actually YCbCr_) with 4:4:4 sampling.

    The ``matrix`` config item chooses the matrix coefficient set. It
    can be ``'601'`` ("`Rec. 601`_", standard definition) or ``'709'``
    ("`Rec. 709`_", high definition). In ``'auto'`` mode the matrix is
    chosen according to the number of lines in the image.

    WARNING: this component assumes RGB input and Y output both have
    black level 0 and white level 255, not the 16..235 range specified
    in Rec 601. See :py:mod:`pyctools.components.colourspace.levels` for
    components to convert the RGB input or Y output. The UV output is in
    the range -112..112.

    .. _Rec. 601: https://en.wikipedia.org/wiki/Rec._601
    .. _Rec. 709: https://en.wikipedia.org/wiki/Rec._709
    .. _YCbCr:    https://en.wikipedia.org/wiki/YCbCr

    """

    outputs = ['output_Y', 'output_UV']     #:

    def initialise(self):
        self.config['matrix'] = ConfigEnum(choices=('auto', '601', '709'))
        self.last_frame_type = None

    def process_frame(self):
        in_frame = self.input_buffer['input'].get()
        Y_frame = self.outframe_pool['output_Y'].get()
        Y_frame.initialise(in_frame)
        UV_frame = self.outframe_pool['output_UV'].get()
        UV_frame.initialise(in_frame)
        if self.transform(in_frame, Y_frame, UV_frame):
            self.send('output_Y', Y_frame)
            self.send('output_UV', UV_frame)
        else:
            self.stop()
            return

    def transform(self, in_frame, Y_frame, UV_frame):
        self.update_config()
        matrix = self.config['matrix']
        # check input and get data
        RGB = in_frame.as_numpy()
        if RGB.shape[2] != 3:
            self.logger.critical('Cannot convert %s images with %d components',
                                 in_frame.type, RGB.shape[2])
            return False
        if in_frame.type != 'RGB' and in_frame.type != self.last_frame_type:
            self.logger.warning('Expected RGB input, got %s', in_frame.type)
        self.last_frame_type = in_frame.type
        # matrix to YUV
        if matrix == 'auto':
            matrix = ('601', '709')[RGB.shape[0] > 576]
        if matrix == '601':
            mat = Matrices.RGBtoYUV_601
        else:
            mat = Matrices.RGBtoYUV_709
        Y_frame.data = ((RGB[:,:,0:1] * mat[0,0]) +
                        (RGB[:,:,1:2] * mat[0,1]) +
                        (RGB[:,:,2:3] * mat[0,2]))
        U = ((RGB[:,:,0] * mat[1,0]) +
             (RGB[:,:,1] * mat[1,1]) +
             (RGB[:,:,2] * mat[1,2]))
        V = ((RGB[:,:,0] * mat[2,0]) +
             (RGB[:,:,1] * mat[2,1]) +
             (RGB[:,:,2] * mat[2,2]))
        UV_frame.data = numpy.dstack((U, V)) * pt_float(224.0 / 255.0)
        Y_frame.type = 'Y'
        UV_frame.type = 'CbCr'
        # audit
        audit = Y_frame.metadata.get('audit')
        audit += 'data = RGBtoY(data)\n'
        audit += '    matrix: {}\n'.format(matrix)
        Y_frame.metadata.set('audit', audit)
        audit = UV_frame.metadata.get('audit')
        audit += 'data = RGBtoUV(data)\n'
        audit += '    matrix: {}\n'.format(matrix)
        UV_frame.metadata.set('audit', audit)
        return True
