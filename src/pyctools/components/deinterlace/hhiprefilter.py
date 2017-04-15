#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2015-17  Pyctools contributors
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

__all__ = ['HHIPreFilter']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.frame import Frame
from pyctools.components.interp.resize import Resize

def HHIPreFilter(config={}):
    """HHI pre-interlace filter.

    A widely used prefilter to prevent line twitter when converting
    sequential images to interlace.

    Coefficients taken from: 'Specification of a Generic Format
    Converter', S. Pigeon, L. Vandendorpe, L. Cuvelier and B. Maison,
    CEC RACE/HAMLET Deliverable no R2110/WP2/DS/S/006/b1, September
    1995. http://www.stephanepigeon.com/Docs/deliv2.pdf

    """

    fil = numpy.array(
        [-4, 8, 25, -123, 230, 728, 230, -123, 25, 8, -4],
        dtype=numpy.float32).reshape((-1, 1, 1)) / numpy.float32(1000)
    resize = Resize(config=config)
    out_frame = Frame()
    out_frame.data = fil
    out_frame.type = 'fil'
    audit = out_frame.metadata.get('audit')
    audit += 'data = HHI pre-interlace filter\n'
    out_frame.metadata.set('audit', audit)
    resize.filter(out_frame)
    return resize
