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

__all__ = ['IntraField']
__docformat__ = 'restructuredtext en'

from pyctools.components.arithmetic import Arithmetic
from pyctools.components.deinterlace.simple import SimpleDeinterlace
from pyctools.components.interp.filtergenerator import FilterGenerator
from pyctools.components.interp.resize import Resize
from pyctools.core.compound import Compound

def IntraField(config={}):
    """Intra field interlace to sequential converter.

    This uses a vertical filter with an aperture of 8 lines, generated
    by
    :py:class:`~pyctools.components.interp.filtergenerator.FilterGenerator`.
    The aperture (and other parameters) can be adjusted after the
    :py:class:`IntraField` component is created.

    """

    return Compound(
        config = config,
        deint = SimpleDeinterlace(),
        interp = Resize(),
        filgen = FilterGenerator(yaperture=8, ycut=50),
        gain = Arithmetic(func='data * pt_float(2)'),
        linkages = {
            ('self',   'input')  : [('deint',  'input')],
            ('deint',  'output') : [('interp', 'input')],
            ('interp', 'output') : [('self',   'output')],
            ('filgen', 'output') : [('gain',   'input')],
            ('gain',   'output') : [('interp', 'filter')],
            }
        )
