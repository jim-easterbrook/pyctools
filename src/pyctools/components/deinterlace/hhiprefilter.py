# This file is part of pyctools http://github.com/jim-easterbrook/pyctools
# Copyright pyctools contributors
# Released under the GNU GPL3 licence

"""HHI pre-interlace filter.

Coefficients taken from: 'Specification of a Generic Format Converter',
S. Pigeon, L. Vandendorpe, L. Cuvelier and B. Maison, CEC RACE/HAMLET
Deliverable no R2110/WP2/DS/S/006/b1, September 1995.
http://www.stephanepigeon.com/Docs/deliv2.pdf

"""

__all__ = ['HHIPreFilter']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.frame import Frame
from pyctools.components.interp.resize import Resize

def HHIPreFilter():
    fil = numpy.array(
        [-4, 8, 25, -123, 230, 728, 230, -123, 25, 8, -4],
        dtype=numpy.float32).reshape((-1, 1, 1)) / numpy.float32(1000)
    resize = Resize()
    out_frame = Frame()
    out_frame.data = fil
    out_frame.type = 'fil'
    audit = out_frame.metadata.get('audit')
    audit += 'data = HHI pre-interlace filter\n'
    out_frame.metadata.set('audit', audit)
    resize.filter(out_frame)
    return resize
