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

from __future__ import print_function

__all__ = ['ColourCorrect']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigFloat
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float

class ColourCorrect(Transformer):
    """Colour correction.

    Apply a 3x3 matrix to RGB inputs to adjust the colours. The six
    parameters set the matrix values. Those on the leading diagonal are
    computed to preserve white balance and overall gain.
    :py:class:`~pyctools.components.arithmetic.Arithmetic` is easily
    used to adjust white balance and gain if needed.

    ===========  =====  ====
    Config
    ===========  =====  ====
    ``RG``       float  Amount of ``G`` input in ``R`` output.
    ``BG``       float  Amount of ``B`` input in ``R`` output.
    ``GR``       float  Amount of ``R`` input in ``G`` output.
    ``GB``       float  Amount of ``B`` input in ``G`` output.
    ``BR``       float  Amount of ``R`` input in ``B`` output.
    ``BG``       float  Amount of ``G`` input in ``B`` output.
    ===========  =====  ====

    """

    def initialise(self):
        self.config['RG'] = ConfigFloat(decimals=2)
        self.config['RB'] = ConfigFloat(decimals=2)
        self.config['GR'] = ConfigFloat(decimals=2)
        self.config['GB'] = ConfigFloat(decimals=2)
        self.config['BR'] = ConfigFloat(decimals=2)
        self.config['BG'] = ConfigFloat(decimals=2)

    def transform(self, in_frame, out_frame):
        self.update_config()
        RG = self.config['RG']
        RB = self.config['RB']
        GR = self.config['GR']
        GB = self.config['GB']
        BR = self.config['BR']
        BG = self.config['BG']
        matrix = numpy.array(
            [[1.0 - (RG + RB), RG,               RB],
             [GR,              1.0 - (GR + GB),  GB],
             [BR,              BG,               1.0 - (BR + BG)]],
             dtype=pt_float)
        in_data = in_frame.as_numpy(dtype=pt_float)
        out_frame.data = numpy.dot(in_data, matrix.T)
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = ColourCorrect(data, {}, {}, {}, {}, {}, {})\n'.format(
            RG, RB, GR, GB, BR, BG)
        out_frame.metadata.set('audit', audit)
        return True
