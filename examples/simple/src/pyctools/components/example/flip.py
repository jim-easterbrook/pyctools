#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-18  Pyctools contributors
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

"""Turn a picture upside down or reflect it left to right.

"""

__all__ = ['Flip']
__docformat__ = 'restructuredtext en'

import PIL.Image

from pyctools.core.base import Transformer
from pyctools.core.config import ConfigEnum

class Flip(Transformer):
    def initialise(self):
        self.config['direction'] = ConfigEnum(choices=('vertical', 'horizontal'))

    def transform(self, in_frame, out_frame):
        self.update_config()
        direction = self.config['direction']
        if direction == 'vertical':
            flip = PIL.Image.FLIP_TOP_BOTTOM
        else:
            flip = PIL.Image.FLIP_LEFT_RIGHT
        in_data = in_frame.as_PIL()
        out_frame.data = in_data.transpose(flip)
        audit = out_frame.metadata.get('audit')
        audit += 'data = Flip(data)\n'
        audit += '    direction: %s\n' % direction
        out_frame.metadata.set('audit', audit)
        return True
