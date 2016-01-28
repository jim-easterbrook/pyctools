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

"""Cython extension for gamma correction component.

"""

from cython.parallel import prange

from libc.math cimport log, sqrt

cimport cython
cimport numpy

ctypedef numpy.float32_t DTYPE_t

@cython.boundscheck(False)
def gamma_frame(numpy.ndarray[DTYPE_t, ndim=3] frame,
                DTYPE_t gamma, DTYPE_t toe, DTYPE_t threshold, DTYPE_t a):
    """Gamma correct a single 3-D :py:class:`numpy.ndarray`.

    The input should be normalised to the range black = 0, white = 1.

    :param numpy.ndarray frame: Input/output image.

    :param DTYPE_t gamma: The gamma power.

    :param DTYPE_t toe: The linear slope.

    :param DTYPE_t threshold: The transition from linear to exponential.

    :param DTYPE_t a: The exponential section gain correction.

    """
    cdef:
        int xlen, ylen, comps
        int x, y, c
        DTYPE_t v
    xlen = frame.shape[1]
    ylen = frame.shape[0]
    comps = frame.shape[2]
    with nogil:
        for y in prange(ylen, schedule='static'):
            for x in range(xlen):
                for c in range(comps):
                    v = frame[y, x, c]
                    if v <= threshold:
                        v *= toe
                    else:
                        v = v ** gamma
                        v = ((1.0 + a) * v) - a
                    frame[y, x, c] = v

@cython.boundscheck(False)
def inverse_gamma_frame(numpy.ndarray[DTYPE_t, ndim=3] frame,
                        DTYPE_t gamma, DTYPE_t toe, DTYPE_t threshold, DTYPE_t a):
    """Inverse gamma correct a single 3-D :py:class:`numpy.ndarray`.

    The input should be normalised to the range black = 0, white = 1.

    :param numpy.ndarray frame: Input/output image.

    :param DTYPE_t gamma: The gamma power.

    :param DTYPE_t toe: The linear slope.

    :param DTYPE_t threshold: The transition from linear to exponential.

    :param DTYPE_t a: The exponential section gain correction.

    """
    cdef:
        int xlen, ylen, comps
        int x, y, c
        DTYPE_t v
    xlen = frame.shape[1]
    ylen = frame.shape[0]
    comps = frame.shape[2]
    with nogil:
        threshold *= toe
        gamma = 1.0 / gamma
        if toe > 0.0:
            toe = 1.0 / toe
        for y in prange(ylen, schedule='static'):
            for x in range(xlen):
                for c in range(comps):
                    v = frame[y, x, c]
                    if v <= threshold:
                        v *= toe
                    else:
                        v = (v + a) / (1.0 + a)
                        v = v ** gamma
                    frame[y, x, c] = v

@cython.boundscheck(False)
def hybrid_gamma_frame(numpy.ndarray[DTYPE_t, ndim=3] frame):
    """Hybrid log-gamma correct a single 3-D :py:class:`numpy.ndarray`.

    The input should be normalised to the range black = 0, white = 1.

    :param numpy.ndarray frame: Input/output image.

    """
    cdef:
        int xlen, ylen, comps
        int x, y, c
        DTYPE_t v, ka, kb, kc
    xlen = frame.shape[1]
    ylen = frame.shape[0]
    comps = frame.shape[2]
    with nogil:
        ka = 0.17883277
        kb = 0.28466892
        kc = 0.55991073
        for y in prange(ylen, schedule='static'):
            for x in range(xlen):
                for c in range(comps):
                    v = frame[y, x, c]
                    if v <= 0.0:
                        v = 0.0
                    elif v <= 1.0:
                        v = 0.5 * sqrt(v)
                    else:
                        v = (ka * log(v - kb)) + kc
                    frame[y, x, c] = v
