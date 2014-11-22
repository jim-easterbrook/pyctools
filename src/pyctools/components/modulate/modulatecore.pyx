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

from cython.parallel import prange
import numpy as np

cimport cython
cimport numpy

DTYPE = np.float32
ctypedef numpy.float32_t DTYPE_t

@cython.boundscheck(False)
cdef void modulate_frame_c(DTYPE_t[:, :, :] out_frame,
                           DTYPE_t[:, :, :] in_frame,
                           DTYPE_t[:, :, :] cell):
    cdef:
        unsigned int xlen, ylen, cells
        unsigned int i, j, x, y, c, c_cell
    with nogil:
        ylen = cell.shape[0]
        xlen = cell.shape[1]
        cells = cell.shape[2]
        for y in prange(in_frame.shape[0], schedule='static'):
            j = y % ylen
            for c in range(in_frame.shape[2]):
                c_cell = c % cells
                for x in range(in_frame.shape[1]):
                    i = x % xlen
                    out_frame[y, x, c] = in_frame[y, x, c] * cell[j, i, c_cell]

@cython.boundscheck(False)
def modulate_frame(numpy.ndarray[DTYPE_t, ndim=3] in_frame,
                   numpy.ndarray[DTYPE_t, ndim=4] cell,
                   unsigned int frame_no):
    cdef:
        unsigned int zlen, k
    zlen = cell.shape[0]
    k = frame_no % zlen
    out_frame = np.empty([in_frame.shape[0], in_frame.shape[1],
                          in_frame.shape[2]], dtype=DTYPE)
    modulate_frame_c(out_frame, in_frame, cell[k])
    return out_frame
