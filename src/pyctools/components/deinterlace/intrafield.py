# This file is part of pyctools http://github.com/jim-easterbrook/pyctools
# Copyright pyctools contributors
# Released under the GNU GPL3 licence

"""Intra field interlace to sequential converter.

"""

__all__ = ['IntraField']
__docformat__ = 'restructuredtext en'

from pyctools.components.arithmetic import Arithmetic
from pyctools.components.deinterlace.simple import SimpleDeinterlace
from pyctools.components.interp.filtergenerator import FilterGenerator
from pyctools.components.interp.resize import Resize
from pyctools.core.compound import Compound

def IntraField():
    return Compound(
        deint = SimpleDeinterlace(),
        interp = Resize(),
        filgen = FilterGenerator(config={'yaperture' : 8, 'ycut' : 50}),
        gain = Arithmetic(config={'func' : 'data * pt_float(2)'}),
        linkages = {
            ('self',   'input')  : [('deint',  'input')],
            ('deint',  'output') : [('interp', 'input')],
            ('interp', 'output') : [('self',   'output')],
            ('filgen', 'output') : [('gain',   'input')],
            ('gain',   'output') : [('interp', 'filter')],
            }
        )
