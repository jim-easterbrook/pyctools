#!/usr/bin/env python
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

"""Fourier transform.

"""

__all__ = ['FFT', 'VisualiseFFT']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.components.arithmetic import Arithmetic
from pyctools.core.config import ConfigEnum
from pyctools.core.base import Transformer
from pyctools.core.types import pt_complex

class FFT(Transformer):
    def initialise(self):
        self.config['inverse'] = ConfigEnum(('off', 'on'), dynamic=True)

    def transform(self, in_frame, out_frame):
        self.update_config()
        inverse = self.config['inverse'] == 'on'
        audit = out_frame.metadata.get('audit')
        audit += 'data = %s(data)\n' % (('FFT', 'IFFT')[inverse])
        out_frame.metadata.set('audit', audit)
        data = in_frame.as_numpy()
        result = []
        for c in range(data.shape[2]):
            result.append(
                (numpy.fft.fft2, numpy.fft.ifft2)[inverse](data[:, :, c]))
        out_frame.data = numpy.dstack(result).astype(pt_complex)
        out_frame.type = 'FT'
        return True


def VisualiseFFT():
    """Convert FFT to a viewable image.

    Computes the logarithmic magnitude of a FFT and scales to 0..255
    range.

    """
    return Arithmetic(
        func='(numpy.log(numpy.absolute(data)) * pt_float(15.0)) + pt_float(40.0)')
