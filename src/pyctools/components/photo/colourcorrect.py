#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2016  Pyctools contributors
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

__all__ = ['ColourCorrect']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigFloat
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float

class ColourCorrect(Transformer):
    """Colour correction.

    Adjust hue and saturation of R, G & B channels separately.

    ===========  =====  ====
    Config
    ===========  =====  ====
    ``gain``     float  Adjust overall gain.
    ``R_hue``    float  Adjust hue of red primary.
    ``R_sat``    float  Adjust saturation of red primary.
    ``G_hue``    float  Adjust hue of green primary.
    ``G_sat``    float  Adjust saturation of green primary.
    ``B_hue``    float  Adjust hue of blue primary.
    ``B_sat``    float  Adjust saturation of blue primary.
    ===========  =====  ====

    """

    def initialise(self):
        self.config['gain'] = ConfigFloat(value=1.0, decimals=2)
        self.config['R_hue'] = ConfigFloat(decimals=2)
        self.config['R_sat'] = ConfigFloat(value=1.0, decimals=2)
        self.config['G_hue'] = ConfigFloat(decimals=2)
        self.config['G_sat'] = ConfigFloat(value=1.0, decimals=2)
        self.config['B_hue'] = ConfigFloat(decimals=2)
        self.config['B_sat'] = ConfigFloat(value=1.0, decimals=2)

    def transform(self, in_frame, out_frame):
        # compute colour matrix
        self.update_config()
        gain = self.config['gain']
        R_hue = self.config['R_hue']
        R_sat = self.config['R_sat']
        G_hue = self.config['G_hue']
        G_sat = self.config['G_sat']
        B_hue = self.config['B_hue']
        B_sat = self.config['B_sat']
        # 'hue' matrix
        hue_matrix = numpy.array(
            [[1.0, 0.0, 0.0],
             [0.0, 1.0, 0.0],
             [0.0, 0.0, 1.0]], dtype=pt_float)
        hue_matrix += numpy.array(
            [[ 0.0, 0.0, 0.0],
             [ 0.5, 0.0, 0.0],
             [-0.5, 0.0, 0.0]], dtype=pt_float) * pt_float(R_hue * R_sat)
        hue_matrix += numpy.array(
            [[0.0,  0.5, 0.0],
             [0.0,  0.0, 0.0],
             [0.0, -0.5, 0.0]], dtype=pt_float) * pt_float(G_hue * G_sat)
        hue_matrix += numpy.array(
            [[0.0, 0.0,  0.5],
             [0.0, 0.0, -0.5],
             [0.0, 0.0,  0.0]], dtype=pt_float) * pt_float(B_hue * B_sat)
        # adjust to preserve white balance
        hue_matrix /= numpy.array(
            [[sum(hue_matrix[0])], [sum(hue_matrix[1])], [sum(hue_matrix[2])]],
            dtype=pt_float)
        # 'saturation' matrix - uses BT.709 RGB->Y as specified by sRGB
        sat_matrix = numpy.array(
            [[1.0, 0.0, 0.0],
             [0.0, 1.0, 0.0],
             [0.0, 0.0, 1.0]], dtype=pt_float)
        sat_matrix += numpy.array(
            [[0.2126 - 1.0, 0.0, 0.0],
             [0.2126,       0.0, 0.0],
             [0.2126,       0.0, 0.0]], dtype=pt_float) * pt_float(1.0 - R_sat)
        sat_matrix += numpy.array(
            [[0.0, 0.7152,       0.0],
             [0.0, 0.7152 - 1.0, 0.0],
             [0.0, 0.7152,       0.0]], dtype=pt_float) * pt_float(1.0 - G_sat)
        sat_matrix += numpy.array(
            [[0.0, 0.0, 0.0722],
             [0.0, 0.0, 0.0722],
             [0.0, 0.0, 0.0722 - 1.0]], dtype=pt_float) * pt_float(1.0 - B_sat)
        matrix = numpy.dot(hue_matrix, sat_matrix) * pt_float(gain)
        # apply matrix
        in_data = in_frame.as_numpy(dtype=pt_float)
        out_frame.data = numpy.dot(in_data, matrix.T)
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = ColourCorrect(data)\n'
        if gain != 1.0:
            audit += '    gain: {}\n'.format(gain)
        if R_hue != 0.0:
            audit += '    R_hue: {}\n'.format(R_hue)
        if R_sat != 1.0:
            audit += '    R_sat: {}\n'.format(R_sat)
        if G_hue != 0.0:
            audit += '    G_hue: {}\n'.format(G_hue)
        if G_sat != 1.0:
            audit += '    G_sat: {}\n'.format(G_sat)
        if B_hue != 0.0:
            audit += '    B_hue: {}\n'.format(B_hue)
        if B_sat != 1.0:
            audit += '    B_sat: {}\n'.format(B_sat)
        out_frame.metadata.set('audit', audit)
        return True
