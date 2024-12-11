#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-24  Pyctools contributors
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
cdef void resize_line(DTYPE_t[:, :] out_line,
                      DTYPE_t[:, :] in_line,
                      DTYPE_t[:, :] norm_filter,
                      int x_up, int x_down) noexcept nogil:
    cdef:
        unsigned int xlen_in, xlen_out, xlen_fil, x_in, x_out, x_fil
        unsigned int comps, filters, c, c_fil
        int x_in_0, x_in_1, x_fil_0, x_fil_off
        DTYPE_t acc
    xlen_in = in_line.shape[0]
    xlen_out = out_line.shape[0]
    xlen_fil = norm_filter.shape[0]
    comps = out_line.shape[1]
    filters = norm_filter.shape[1]
    # offset as filter is symmetrical
    x_fil_off = (xlen_fil - 1) // 2
    for c in range(comps):
        c_fil = c % filters
        for x_out in range(xlen_out):
            x_fil_0 = -x_fil_off
            x_in_1 = min(((<int>x_out * x_down) + x_up - x_fil_0) // x_up, xlen_in)
            x_fil_0 = (<int>xlen_fil - 1) - x_fil_off
            x_in_0 = max(((<int>x_out * x_down) + (x_up - 1) - x_fil_0) // x_up, 0)
            x_fil_0 = ((<int>x_out * x_down) - (x_in_0 * x_up)) + x_fil_off
            acc = out_line[x_out, c]
            x_fil = x_fil_0
            for x_in in range(x_in_0, x_in_1):
                acc += in_line[x_in, c] * norm_filter[x_fil, c_fil]
                x_fil -= x_up
            out_line[x_out, c] = acc

@cython.boundscheck(False)
cdef void filter_line(DTYPE_t[:, :] out_line,
                      DTYPE_t[:, :] in_line,
                      DTYPE_t[:, :] norm_filter,
                      int x_up, int x_down) noexcept nogil:
    cdef:
        unsigned int xlen_in, xlen_out, xlen_fil, x_in, x_out, x_fil
        unsigned int comps, filters, c, c_fil
        int x_in_0, x_in_1, x_fil_0, x_fil_off
        DTYPE_t acc
    xlen_in = in_line.shape[0]
    xlen_out = out_line.shape[0]
    xlen_fil = norm_filter.shape[0]
    comps = out_line.shape[1]
    filters = norm_filter.shape[1]
    # offset as filter is symmetrical
    x_fil_off = (xlen_fil - 1) // 2
    for c in range(comps):
        c_fil = c % filters
        for x_out in range(xlen_out):
            x_fil_0 = -x_fil_off
            x_in_1 = min(<int>x_out + 1 - x_fil_0, xlen_in)
            x_fil_0 = (<int>xlen_fil - 1) - x_fil_off
            x_in_0 = max(<int>x_out - x_fil_0, 0)
            x_fil_0 = (<int>x_out - x_in_0) + x_fil_off
            acc = out_line[x_out, c]
            x_fil = x_fil_0
            for x_in in range(x_in_0, x_in_1):
                acc += in_line[x_in, c] * norm_filter[x_fil, c_fil]
                x_fil -= 1
            out_line[x_out, c] = acc

@cython.boundscheck(False)
cdef void scale_line(DTYPE_t[:, :] out_line,
                     DTYPE_t[:, :] in_line,
                     DTYPE_t[:, :] norm_filter,
                     int x_up, int x_down) noexcept nogil:
    cdef:
        unsigned int xlen, x
        unsigned int comps, filters, c
        DTYPE_t coef
    xlen = out_line.shape[0]
    comps = out_line.shape[1]
    filters = norm_filter.shape[1]
    for c in range(comps):
        coef = norm_filter[0, c % filters]
        if coef != 0.0:
            for x in range(xlen):
                out_line[x, c] += in_line[x, c] * coef

@cython.boundscheck(False)
cdef void resize_frame_core(DTYPE_t[:, :, :] out_frame,
                            DTYPE_t[:, :, :] in_frame,
                            DTYPE_t[:, :, :] norm_filter,
                            int x_up, int x_down, int y_up, int y_down):
    cdef:
        int ylen_in
        int ylen_out
        int xlen_fil, ylen_fil, y_fil_off
        int y_in_0, y_in_1, y_in
        int y_out
        int y_fil
        void (*interp)(DTYPE_t[:, :], DTYPE_t[:, :], DTYPE_t[:, :],
                       int, int) noexcept nogil
    with nogil:
        ylen_in = in_frame.shape[0]
        ylen_out = out_frame.shape[0]
        xlen_fil = norm_filter.shape[1]
        ylen_fil = norm_filter.shape[0]
        # choice of filter coefficient is according to
        #   filter_pos = (out_pos * down) - (in_pos * up)
        if x_up != 1 or x_down != 1:
            interp = &resize_line
        elif xlen_fil == 1:
            # pure vertical filter
            interp = &scale_line
        else:
            # horizontal filtering without resizing
            interp = &filter_line
        # offset as filter is symmetrical
        y_fil_off = (ylen_fil - 1) // 2
        for y_out in prange(ylen_out, schedule='static'):
            y_fil = -y_fil_off
            y_in_1 = min(((y_out * y_down) + y_up + y_fil_off) // y_up, ylen_in)
            y_fil = (ylen_fil - 1) - y_fil_off
            y_in_0 = max(((y_out * y_down) + (y_up - 1) - y_fil) // y_up, 0)
            y_fil = ((y_out * y_down) - (y_in_0 * y_up)) + y_fil_off
            for y_in in range(y_in_0, y_in_1):
                interp(out_frame[y_out], in_frame[y_in], norm_filter[y_fil],
                       x_up, x_down)
                y_fil = y_fil - y_up

def resize_frame(numpy.ndarray[DTYPE_t, ndim=3] in_frame,
                 numpy.ndarray[DTYPE_t, ndim=3] norm_filter,
                 int x_up, int x_down, int y_up, int y_down):
    """Filter and resize a single 3-D :py:class:`numpy.ndarray`.

    This is the core of the :py:class:`Resize` component but can also be
    used by other components (such as :py:mod:`YUVtoRGB
    <pyctools.components.colourspace.yuvtorgb>`) that need high speed
    image filtering or interpolation.

    The filter should be "normalised" so that the coefficients in each
    phase sum to unity. This is typically done by multiplying the
    filter coefficients by the horizontal and vertical up-conversion
    factors.

    :param numpy.ndarray in_frame: Input image.

    :param numpy.ndarray norm_filter: Normalised filter.

    :param int x_up: Horizontal up-conversion factor.

    :param int x_down: Horizontal down-conversion factor.

    :param int y_up: Vertical up-conversion factor.

    :param int y_down: Vertical down-conversion factor.

    :return: A :py:class:`numpy.ndarray` object containing the new
        image.

    """
    cdef:
        int xlen_in, ylen_in, comps
        int xlen_out, ylen_out
        numpy.ndarray[DTYPE_t, ndim=3] out_frame
    xlen_in = in_frame.shape[1]
    ylen_in = in_frame.shape[0]
    comps = in_frame.shape[2]
    xlen_out = ((xlen_in * x_up) + (x_down // 2)) // x_down
    ylen_out = ((ylen_in * y_up) + (y_down // 2)) // y_down
    xlen_out = max(xlen_out, 1)
    ylen_out = max(ylen_out, 1)
    out_frame = np.zeros(([ylen_out, xlen_out, comps]), dtype=DTYPE)
    resize_frame_core(
        out_frame, in_frame, norm_filter, x_up, x_down, y_up, y_down)
    return out_frame
