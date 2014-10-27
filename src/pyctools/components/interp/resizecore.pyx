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

import numpy

cimport cython
cimport numpy

ctypedef numpy.float32_t DTYPE_t

@cython.boundscheck(False)
cdef void resize_line(DTYPE_t[:] out_line,
                      DTYPE_t[:] in_line,
                      DTYPE_t[:] norm_filter,
                      int x_up, int x_down) nogil:
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

@cython.boundscheck(False)
cdef void scale_line(DTYPE_t[:] out_line,
                     DTYPE_t[:] in_line,
                     DTYPE_t[:] norm_filter,
                     int x_up, int x_down) nogil:
    cdef:
        unsigned int xlen, x
        DTYPE_t coef
    xlen = out_line.shape[0]
    coef = norm_filter[0]
    for x in range(xlen):
        out_line[x] += in_line[x] * coef

@cython.boundscheck(False)
cdef void resize_frame_core(DTYPE_t[:, :] out_comp,
                            DTYPE_t[:, :] in_comp,
                            DTYPE_t[:, :] norm_filter,
                            int x_up, int x_down, int y_up, int y_down) nogil:
    cdef:
        int xlen_in, ylen_in
        int xlen_out, ylen_out
        int xlen_fil, ylen_fil, y_fil_off
        int y_in_0, y_in_1, y_in
        int y_out
        int y_fil
        void (*interp)(DTYPE_t[:], DTYPE_t[:], DTYPE_t[:], int, int) nogil
    xlen_in = in_comp.shape[1]
    ylen_in = in_comp.shape[0]
    xlen_out = out_comp.shape[1]
    ylen_out = out_comp.shape[0]
    xlen_fil = norm_filter.shape[1]
    ylen_fil = norm_filter.shape[0]
    # choice of filter coefficient is according to
    #   filter_pos = (out_pos * down) - (in_pos * up)
    if x_up == 1 and x_down == 1 and xlen_fil == 1:
        # pure vertical filter
        interp = &scale_line
    else:
        interp = &resize_line
    # offset as filter is symmetrical
    y_fil_off = (ylen_fil - 1) // 2
    for y_out in range(ylen_out):
        y_fil = -y_fil_off
        y_in_1 = min(((y_out * y_down) + y_up + y_fil_off) // y_up, ylen_in)
        y_fil = (ylen_fil - 1) - y_fil_off
        y_in_0 = max(((y_out * y_down) + (y_up - 1) - y_fil) // y_up, 0)
        y_fil = ((y_out * y_down) - (y_in_0 * y_up)) + y_fil_off
        for y_in in range(y_in_0, y_in_1):
            interp(out_comp[y_out], in_comp[y_in], norm_filter[y_fil],
                   x_up, x_down)
            y_fil -= y_up

def resize_frame(numpy.ndarray[DTYPE_t, ndim=2] in_comp,
                 numpy.ndarray[DTYPE_t, ndim=2] norm_filter,
                 int x_up, int x_down, int y_up, int y_down):
    cdef:
        int xlen_in, ylen_in
        int xlen_out, ylen_out
        numpy.ndarray[DTYPE_t, ndim=2] out_comp
    xlen_in = in_comp.shape[1]
    ylen_in = in_comp.shape[0]
    xlen_out = (xlen_in * x_up) // x_down
    ylen_out = (ylen_in * y_up) // y_down
    xlen_out = max(xlen_out, 1)
    ylen_out = max(ylen_out, 1)
    out_comp = numpy.zeros(([ylen_out, xlen_out]), dtype=numpy.float32)
    resize_frame_core(
        out_comp, in_comp, norm_filter, x_up, x_down, y_up, y_down)
    return out_comp
