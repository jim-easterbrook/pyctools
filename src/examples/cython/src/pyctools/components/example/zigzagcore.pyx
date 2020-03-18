#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-20  Jim Easterbrook  jim@jim-easterbrook.me.uk
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

"""Cython extension for Zigzag component.

"""

from __future__ import absolute_import

cimport cython
from cython.parallel import prange
cimport numpy
import numpy

DTYPE = numpy.float32
ctypedef numpy.float32_t DTYPE_t

cdef extern from "math.h" nogil:
    float sinf(float x)

@cython.boundscheck(False)
def zigzag_frame(numpy.ndarray[DTYPE_t, ndim=3] in_frame,
                 float amplitude, float period):
    cdef:
        unsigned int xlen, ylen, comps
        unsigned int x, y, x_in, c
        int offset
        numpy.ndarray[DTYPE_t, ndim=3] out_frame
    xlen = in_frame.shape[1]
    ylen = in_frame.shape[0]
    comps = in_frame.shape[2]
    out_frame = numpy.ndarray([ylen, xlen, comps], dtype=DTYPE)
    with nogil:
        for y in prange(ylen, schedule='static'):
            offset = <int>(amplitude * sinf(y * 2 * 3.1415926 / period))
            for x in range(xlen):
                x_in = (<int>x + xlen + offset) % xlen
                for c in range(comps):
                    out_frame[y, x, c] = in_frame[y, x_in, c]
    return out_frame
