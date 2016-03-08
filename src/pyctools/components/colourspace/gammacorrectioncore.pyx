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

from cython.parallel import prange

cimport cython
cimport numpy

ctypedef numpy.float32_t DTYPE_t

@cython.boundscheck(False)
def apply_transfer_function(numpy.ndarray[DTYPE_t, ndim=3] frame,
                            numpy.ndarray[DTYPE_t, ndim=1] in_val,
                            numpy.ndarray[DTYPE_t, ndim=1] out_val):
    """Apply a transfer function to a single 3-D :py:class:`numpy.ndarray`.

    The function is defined by two 1-D arrays - input values ``in_val``
    and the corresponding output values ``out_val``. Linear
    interpolation is used to map input values that lie between members
    of the ``in_val`` list. Input values outside the range of ``in_val``
    are mapped by extrapolation from the first or last two values.

    :param numpy.ndarray frame: Input/output image.

    :param numpy.ndarray in_val: Function inputs.

    :param numpy.ndarray out_val: Function outputs.

    """
    cdef:
        int xlen, ylen, comps, points
        int x, y, c, i
        DTYPE_t v, d_in, d_out
    xlen = frame.shape[1]
    ylen = frame.shape[0]
    comps = frame.shape[2]
    points = in_val.shape[0]
    with nogil:
        for y in prange(ylen, schedule='static'):
            i = 0
            for c in range(comps):
                for x in range(xlen):
                    v = frame[y, x, c]
                    # find bracketing input values
                    while i + 1 < points - 1 and v > in_val[i+1]:
                        i = i + 1
                    while i > 0 and v < in_val[i]:
                        i = i - 1
                    # do linear interpolation (or extrapolation if outside range)
                    d_in = in_val[i+1] - in_val[i]
                    d_out = out_val[i+1] - out_val[i]
                    if d_in == 0.0:
                        frame[y, x, c] = out_val[i] + (d_out * 0.5)
                    else:
                        frame[y, x, c] = out_val[i] + (
                            d_out * (v - in_val[i]) / d_in)
