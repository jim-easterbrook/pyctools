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

"""Vignette correction.

Adjust the brightness of images with a radially varying gain function.
This should be applied to 'linear intensity' image data before gamma
correction is applied.

The ``range`` config item specifies the input and output video ranges.
It can be either ``'studio'`` (16..235) or ``'computer'`` (0..255).

The ``r1``, ``r2`` and ``r3`` parameters set how the correction varies
with radius, radius ** 2 and radius ** 3. The first affects the whole
picture, the higher powers have more effect at the edges.

===========  =====  ====
Config
===========  =====  ====
``range``    str    Nominal black and white levels. Can be ``'studio'`` or ``'computer'``.
``r1``       float  Amount of radius correction
``r2``       float  Amount of radius^2 correction
``r3``       float  Amount of radius^3 correction
===========  =====  ====

"""

__all__ = ['VignetteCorrector']
__docformat__ = 'restructuredtext en'

import math

import numpy

from pyctools.core.config import ConfigEnum, ConfigFloat
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float

class VignetteCorrector(Transformer):
    def initialise(self):
        self.config['range'] = ConfigEnum(('studio', 'computer'))
        self.config['r1'] = ConfigFloat(decimals=2)
        self.config['r2'] = ConfigFloat(decimals=2)
        self.config['r3'] = ConfigFloat(decimals=2)
        self.gain = None

    def transform(self, in_frame, out_frame):
        if self.update_config():
            self.gain = None
        # get data
        data = in_frame.as_numpy(dtype=pt_float)
        # generate correction function
        r1 = self.config['r1']
        r2 = self.config['r2']
        r3 = self.config['r3']
        h, w = data.shape[:2]
        if self.gain is None or self.gain.shape != [h, w, 1]:
            self.gain = numpy.empty((h, w, 1), dtype=pt_float)
            xc = float(w - 1) / 2.0
            yc = float(h - 1) / 2.0
            r0 = math.sqrt((xc ** 2) + (yc ** 2))
            for y in range(h):
                y2 = (float(y) - yc) ** 2
                for x in range(w):
                    x2 = (float(x) - xc) ** 2
                    r = math.sqrt(x2 + y2) / r0
                    self.gain[y, x, 0] = (
                        1.0 + (r1 * r) + (r2 * (r ** 2)) + (r3 * (r ** 3)))
        # subtract black level
        if self.config['range'] == 'studio':
            data -= pt_float(16.0)
        # apply correction
        data *= self.gain
        # restore black level
        if self.config['range'] == 'studio':
            data += pt_float(16.0)
        out_frame.data = data
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = VignetteCorrector(data, {}, {}, {})\n'.format(r1, r2, r3)
        out_frame.metadata.set('audit', audit)
        return True
