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

"""Cython extension for zone plate generator.

"""

cimport cython
cimport numpy

ctypedef numpy.float32_t DTYPE_t

@cython.boundscheck(False)
def zone_frame(numpy.ndarray[DTYPE_t, ndim=2] out_frame,
               numpy.ndarray[DTYPE_t, ndim=1] waveform,
               unsigned int z, DTYPE_t k0,
               DTYPE_t kx, DTYPE_t ky, DTYPE_t kt,
               DTYPE_t kx2, DTYPE_t kxy, DTYPE_t kxt,
               DTYPE_t kyx, DTYPE_t ky2, DTYPE_t kyt,
               DTYPE_t ktx, DTYPE_t kty, DTYPE_t kt2):
    cdef:
        unsigned int xlen, ylen, x, y
        DTYPE_t phases
        DTYPE_t Ikxtdt_kx, Ikytdt_ky, Ikt2dt_kt, Iktdt_k0
        DTYPE_t Ikydy_Iktdt_k0, Iky2dy_Ikytdt_ky, Ikxydy_Ikxtdt_kx
        DTYPE_t Ikxdx_Ikydy_Iktdt_k0, Ikx2dx_Ikxydy_Ikxtdt_kx
    xlen = out_frame.shape[1]
    ylen = out_frame.shape[0]
    phases = waveform.shape[0]
    # compute temporal integrals
    Ikxtdt_kx = kx + ((kxt + ktx) * z)
    Ikytdt_ky = ky + ((kyt + kty) * z)
    Ikt2dt_kt = kt +  (kt2        * z)
    Iktdt_k0 = k0 + (Ikt2dt_kt * z)
    # initialise vertical integrals
    Ikydy_Iktdt_k0 = Iktdt_k0 % phases
    Iky2dy_Ikytdt_ky = Ikytdt_ky
    Ikxydy_Ikxtdt_kx = Ikxtdt_kx
    for y in range(ylen):
        # initialise horizontal integrals
        Ikxdx_Ikydy_Iktdt_k0 = Ikydy_Iktdt_k0
        Ikx2dx_Ikxydy_Ikxtdt_kx = Ikxydy_Ikxtdt_kx
        for x in range(xlen):
            out_frame[y, x] = waveform[int(Ikxdx_Ikydy_Iktdt_k0)]
            # increment horizontal integrals
            Ikxdx_Ikydy_Iktdt_k0 = (
                Ikxdx_Ikydy_Iktdt_k0 + Ikx2dx_Ikxydy_Ikxtdt_kx) % phases
            Ikx2dx_Ikxydy_Ikxtdt_kx += kx2
        # increment vertical integrals
        Ikydy_Iktdt_k0 = (Ikydy_Iktdt_k0 + Iky2dy_Ikytdt_ky) % phases
        Iky2dy_Ikytdt_ky += ky2
        Ikxydy_Ikxtdt_kx += kxy + kyx
