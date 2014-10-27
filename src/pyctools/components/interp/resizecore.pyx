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
cimport numpy

ctypedef numpy.float32_t DTYPE_t

@cython.boundscheck(False)
def resize_line(numpy.ndarray[DTYPE_t, ndim=1] out_line,
                numpy.ndarray[DTYPE_t, ndim=1] in_line,
                numpy.ndarray[DTYPE_t, ndim=1] norm_filter,
                int x_up, int x_down):
    cdef:
        unsigned int xlen_in, xlen_out, xlen_fil, x_in, x_out, x_fil
        int x_in_0, x_in_1, x_fil_0, x_fil_off
        DTYPE_t acc
    xlen_in = in_line.shape[0]
    xlen_out = out_line.shape[0]
    xlen_fil = norm_filter.shape[0]
    # offset as filter is symmetrical
    x_fil_off = (xlen_fil - 1) // 2
    for x_out in range(xlen_out):
        x_fil_0 = -x_fil_off
        x_in_1 = min(((<int>x_out * x_down) + x_up - x_fil_0) // x_up, xlen_in)
        x_fil_0 = (<int>xlen_fil - 1) - x_fil_off
        x_in_0 = max(((<int>x_out * x_down) + (x_up - 1) - x_fil_0) // x_up, 0)
        x_fil_0 = ((<int>x_out * x_down) - (x_in_0 * x_up)) + x_fil_off
        acc = out_line[x_out]
        x_fil = x_fil_0
        for x_in in range(x_in_0, x_in_1):
            acc += in_line[x_in] * norm_filter[x_fil]
            x_fil -= x_up
        out_line[x_out] = acc
