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

DTYPE = numpy.float32
ctypedef numpy.float32_t DTYPE_t

@cython.boundscheck(False)
def resize_line1(numpy.ndarray[DTYPE_t, ndim=1] out_line,
                 numpy.ndarray[DTYPE_t, ndim=1] in_line,
                 numpy.ndarray[DTYPE_t, ndim=1] norm_filter,
                 unsigned int x_up, unsigned int x_down):
    cdef unsigned int xlen_in = in_line.shape[0]
    cdef unsigned int xlen_out = out_line.shape[0]
    cdef unsigned int xlen_fil = norm_filter.shape[0]
    cdef unsigned int d_fil = x_up * x_down
    cdef unsigned int x_in_phase, x_out_phase, x_in_0, x_out_0
    cdef unsigned int x_in, x_out, x_fil
    cdef int x_fil_0
    cdef DTYPE_t coef
    for x_in_phase in range(x_down):
        for x_out_phase in range(x_up):
            x_in_0 = x_in_phase
            x_out_0 = x_out_phase
            x_fil_0 = (x_out_0 * x_down) - (x_in_0 * x_up)
            # add offset as filter aperture is symmetrical
            x_fil_0 += (xlen_fil - 1) // 2
            # find lowest coefficient for this phase
            while x_fil_0 >= d_fil:
                x_fil_0 -= d_fil
                x_in_0 += x_down
            while x_fil_0 < 0:
                x_fil_0 += d_fil
                x_out_0 += x_up
            # iterate over all coefficients for this phase
            for x_fil in range(x_fil_0, xlen_fil, d_fil):
                coef = norm_filter[x_fil]
                if coef != 0.0:
                    x_in = x_in_0
                    for x_out in range(x_out_0, xlen_out, x_up):
                        out_line[x_out] += in_line[x_in] * coef
                        x_in += x_down
                        if x_in >= xlen_in:
                            break
                # increment x_in_0 or x_out_0 to match increment in x_fil
                if x_in_0 >= x_down:
                    x_in_0 -= x_down
                else:
                    x_out_0 += x_up

@cython.boundscheck(False)
def resize_line2(numpy.ndarray[DTYPE_t, ndim=2] out_line,
                 numpy.ndarray[DTYPE_t, ndim=2] in_line,
                 numpy.ndarray[DTYPE_t, ndim=1] norm_filter,
                 unsigned int x_up, unsigned int x_down):
    cdef unsigned int xlen_in = in_line.shape[0]
    cdef unsigned int xlen_out = out_line.shape[0]
    cdef unsigned int xlen_fil = norm_filter.shape[0]
    cdef unsigned int comps = in_line.shape[1]
    cdef unsigned int d_fil = x_up * x_down
    cdef unsigned int x_in_phase, x_out_phase, x_in_0, x_out_0
    cdef unsigned int x_in, x_out, x_fil, c
    cdef int x_fil_0
    cdef DTYPE_t coef
    for x_in_phase in range(x_down):
        for x_out_phase in range(x_up):
            x_in_0 = x_in_phase
            x_out_0 = x_out_phase
            x_fil_0 = (x_out_0 * x_down) - (x_in_0 * x_up)
            # add offset as filter aperture is symmetrical
            x_fil_0 += (xlen_fil - 1) // 2
            # find lowest coefficient for this phase
            while x_fil_0 >= d_fil:
                x_fil_0 -= d_fil
                x_in_0 += x_down
            while x_fil_0 < 0:
                x_fil_0 += d_fil
                x_out_0 += x_up
            # iterate over all coefficients for this phase
            for x_fil in range(x_fil_0, xlen_fil, d_fil):
                coef = norm_filter[x_fil]
                if coef != 0.0:
                    x_in = x_in_0
                    for x_out in range(x_out_0, xlen_out, x_up):
                        for c in range(comps):
                            out_line[x_out, c] += in_line[x_in, c] * coef
                        x_in += x_down
                        if x_in >= xlen_in:
                            break
                # increment x_in_0 or x_out_0 to match increment in x_fil
                if x_in_0 >= x_down:
                    x_in_0 -= x_down
                else:
                    x_out_0 += x_up
