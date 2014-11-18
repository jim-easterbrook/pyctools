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

"""Distort a picture with a zigzag pattern.

"""

__all__ = ['Zigzag']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.base import Transformer
from pyctools.core.config import ConfigFloat
from .zigzagcore import zigzag_frame

class Zigzag(Transformer):
    def initialise(self):
        self.config['amplitude'] = ConfigFloat(value=10.0)
        self.config['period'] = ConfigFloat(value=100.0)

    def transform(self, in_frame, out_frame):
        self.update_config()
        amplitude = self.config['amplitude']
        period = self.config['period']
        out_frame.data = []
        for in_data in in_frame.as_numpy(dtype=numpy.float32, dstack=False):
            out_frame.data.append(zigzag_frame(in_data, amplitude, period))
        audit = out_frame.metadata.get('audit')
        audit += 'data = Zigzag(data)\n'
        audit += '    amplitude: %g, period: %g\n' % (amplitude, period)
        out_frame.metadata.set('audit', audit)
        return True
