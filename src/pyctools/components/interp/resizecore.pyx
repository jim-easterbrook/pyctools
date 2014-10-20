#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014  Jim Easterbrook  jim@jim-easterbrook.me.uk
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

"""Cython extension for interpolation components.

"""

cimport cython
import numpy
cimport numpy

ctypedef numpy.float32_t DTYPE_t

@cython.boundscheck(False)
def resize_line1(numpy.ndarray[DTYPE_t, ndim=1] out_line,
                 numpy.ndarray[DTYPE_t, ndim=1] in_line,
                 numpy.ndarray[DTYPE_t, ndim=1] norm_filter,
                 int x_up, int x_down):
    cdef:
        int xlen_in, xlen_out, xlen_fil
        int x_in, x_out, x_fil, x_fil_off
        DTYPE_t acc
    xlen_in = in_line.shape[0]
    xlen_out = out_line.shape[0]
    xlen_fil = norm_filter.shape[0]
    # offset as filter is symmetrical
    x_fil_off = (xlen_fil - 1) // 2
    for x_out in range(xlen_out):
        x_fil = (xlen_fil - 1) - x_fil_off
        x_in = max(((x_out * x_down) + (x_up - 1) - x_fil) // x_up, 0)
        x_fil = ((x_out * x_down) - (x_in * x_up)) + x_fil_off
        acc = out_line[<unsigned int>x_out]
        while x_fil >= 0 and x_in < xlen_in:
            acc += in_line[<unsigned int>x_in] * norm_filter[<unsigned int>x_fil]
            x_fil -= x_up
            x_in += 1
        out_line[x_out] = acc

@cython.boundscheck(False)
def resize_line2(numpy.ndarray[DTYPE_t, ndim=2] out_line,
                 numpy.ndarray[DTYPE_t, ndim=2] in_line,
                 numpy.ndarray[DTYPE_t, ndim=1] norm_filter,
                 int x_up, int x_down):
    cdef:
        int xlen_in, xlen_out, xlen_fil
        int x_in, x_out, x_fil, x_fil_off, x_in_0, x_fil_0
        unsigned int comps, c
        DTYPE_t acc
    xlen_in = in_line.shape[0]
    xlen_out = out_line.shape[0]
    xlen_fil = norm_filter.shape[0]
    comps = in_line.shape[1]
    # offset as filter is symmetrical
    x_fil_off = (xlen_fil - 1) // 2
    for x_out in range(xlen_out):
        x_fil = (xlen_fil - 1) - x_fil_off
        x_in_0 = max(((x_out * x_down) + (x_up - 1) - x_fil) // x_up, 0)
        x_fil_0 = ((x_out * x_down) - (x_in_0 * x_up)) + x_fil_off
        for c in range(comps):
            x_in = x_in_0
            x_fil = x_fil_0
            acc = out_line[<unsigned int>x_out, c]
            while x_fil >= 0 and x_in < xlen_in:
                acc += in_line[<unsigned int>x_in, c] * norm_filter[<unsigned int>x_fil]
                x_fil -= x_up
                x_in += 1
            out_line[x_out, c] = acc
