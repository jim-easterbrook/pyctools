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

from __future__ import print_function

__all__ = ['YUVtoRGB']
__docformat__ = 'restructuredtext en'

import cv2
import numpy

from pyctools.core.config import ConfigEnum
from pyctools.core.base import Component
from pyctools.core.types import pt_float
from pyctools.components.interp.resize import resize_frame
from .matrices import Matrices


class YUVtoRGB(Component):
    """YUV (YCbCr) to RGB converter.

    Convert "YUV" (actually YCbCr) frames (with any UV subsampling) to
    RGB.

    For ``4:2:2`` subsampling a high quality resampling filter is used,
    as specified in `BBC R&D Report 1984/04
    <http://www.bbc.co.uk/rd/publications/rdreport_1984_04>`_. For other
    subsampling patterns, where the correct filtering is less well
    specified, simple bicubic interpolation is used.

    The ``matrix`` config item chooses the matrix coefficient set. It
    can be ``'601'`` ("`Rec. 601`_", standard definition) or ``'709'``
    ("`Rec. 709`_", high definition). In ``'auto'`` mode the matrix is
    chosen according to the number of lines in the image.

    WARNING: this component assumes Y input and RGB output both have
    black level 0 and white level 255, not the 16..235 range specified
    in Rec 601. See :py:mod:`pyctools.components.colourspace.levels` for
    components to convert the Y input or RGB output. The UV input should
    be in the range -112..112.

    .. _Rec. 601: https://en.wikipedia.org/wiki/Rec._601
    .. _Rec. 709: https://en.wikipedia.org/wiki/Rec._709
    .. _YCbCr:    https://en.wikipedia.org/wiki/YCbCr

    """

    filter_21 = numpy.array([
        -0.002913300, 0.0,  0.010153700, 0.0, -0.022357799, 0.0,
         0.044929001, 0.0, -0.093861297, 0.0,  0.314049691, 0.5,
         0.314049691, 0.0, -0.093861297, 0.0,  0.044929001, 0.0,
        -0.022357799, 0.0,  0.010153700, 0.0, -0.002913300
        ], dtype=pt_float).reshape(1, -1, 1)
    inputs = ['input_Y', 'input_UV']    #:

    def initialise(self):
        self.config['matrix'] = ConfigEnum(choices=('auto', '601', '709'))
        self.last_frame_type = None

    def process_frame(self):
        Y_frame = self.input_buffer['input_Y'].get()
        UV_frame = self.input_buffer['input_UV'].get()
        out_frame = self.outframe_pool['output'].get()
        out_frame.initialise(Y_frame)
        if self.transform(Y_frame, UV_frame, out_frame):
            self.send('output', out_frame)
        else:
            self.stop()
            return

    def transform(self, Y_frame, UV_frame, out_frame):
        self.update_config()
        matrix = self.config['matrix']
        # check input and get data
        Y = Y_frame.as_numpy()
        if Y.shape[2] != 1:
            self.logger.critical('Y input has %d components', Y.shape[2])
            return False
        UV = UV_frame.as_numpy() * pt_float(255.0 / 224.0)
        if UV.shape[2] != 2:
            self.logger.critical('UV input has %d components', UV.shape[2])
            return False
        # resample U & V
        v_ss = Y.shape[0] // UV.shape[0]
        h_ss = Y.shape[1] // UV.shape[1]
        if h_ss == 2:
            UV = resize_frame(UV, self.filter_21, 2, 1, 1, 1)
        elif h_ss != 1:
            UV = cv2.resize(
                UV, None, fx=h_ss, fy=1, interpolation=cv2.INTER_CUBIC)
        if v_ss != 1:
            UV = cv2.resize(
                UV, None, fx=1, fy=v_ss, interpolation=cv2.INTER_CUBIC)
        # matrix to RGB
        if matrix == 'auto':
            matrix = ('601', '709')[RGB.shape[0] > 576]
        if matrix == '601':
            mat = Matrices.YUVtoRGB_601
        else:
            mat = Matrices.YUVtoRGB_709
        R = ((Y[:,:,0] * mat[0,0]) +
             (UV[:,:,0] * mat[0,1]) +
             (UV[:,:,1] * mat[0,2]))
        G = ((Y[:,:,0] * mat[1,0]) +
             (UV[:,:,0] * mat[1,1]) +
             (UV[:,:,1] * mat[1,2]))
        B = ((Y[:,:,0] * mat[2,0]) +
             (UV[:,:,0] * mat[2,1]) +
             (UV[:,:,1] * mat[2,2]))
        out_frame.data = numpy.dstack((R, G, B))
        out_frame.type = 'RGB'
        # audit
        audit = 'Y = {\n'
        for line in Y_frame.metadata.get('audit').splitlines():
            audit += '    ' + line + '\n'
        audit += '    }\n'
        audit += 'UV = {\n'
        for line in UV_frame.metadata.get('audit').splitlines():
            audit += '    ' + line + '\n'
        audit += '    }\n'
        audit += 'data = YUVtoRGB(Y, UV)\n'
        audit += '    matrix: {}\n'.format(matrix)
        out_frame.metadata.set('audit', audit)
        return True
