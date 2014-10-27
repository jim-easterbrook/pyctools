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

cimport cython
cimport numpy

ctypedef numpy.float32_t DTYPE_t

@cython.boundscheck(False)
def modulate_frame(numpy.ndarray[DTYPE_t, ndim=2] out_comp,
                   numpy.ndarray[DTYPE_t, ndim=2] in_comp,
                   numpy.ndarray[DTYPE_t, ndim=3] cell,
                   unsigned int frame_no):
    cdef:
        unsigned int xlen, ylen, zlen
        unsigned int i, j, k, x, y
    zlen = cell.shape[0]
    ylen = cell.shape[1]
    xlen = cell.shape[2]
    k = frame_no % zlen
    for y in range(in_comp.shape[0]):
        j = y % ylen
        for x in range(in_comp.shape[1]):
            i = x % xlen
            out_comp[y, x] = in_comp[y, x] * cell[k, j, i]
