#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2019  Pyctools contributors
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

"""Standard RGB to YUV matrices for use in other components.

Values taken from: https://en.wikipedia.org/wiki/YCbCr
"""

import numpy

from pyctools.core.types import pt_float


def matrix_from_K_values(KR, KB):
    KG = 1.0 - (KR + KB)
    DB = 2.0 * (1.0 - KB)
    DR = 2.0 * (1.0 - KR)
    return numpy.array(
        [[ KR,       KG,       KB],
         [-KR / DB, -KG / DB,  0.5],
         [ 0.5,     -KG / DR, -KB / DR]],
        dtype=pt_float)


class Matrices(object):
    RGBtoYUV_601 = numpy.array(
        [[ 0.299,     0.587,     0.114],
         [-0.168736, -0.331264,  0.5],
         [ 0.5,      -0.418688, -0.081312]], dtype=pt_float)
    RGBtoYUV_709 = matrix_from_K_values(0.2126, 0.0722)
    YUVtoRGB_601 = numpy.linalg.inv(RGBtoYUV_601)
    YUVtoRGB_709 = numpy.linalg.inv(RGBtoYUV_709)
