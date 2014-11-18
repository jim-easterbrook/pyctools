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

"""Turn a picture upside down.

"""

__all__ = ['Flip']
__docformat__ = 'restructuredtext en'

import PIL.Image

from pyctools.core.base import Transformer

class Flip(Transformer):
    def transform(self, in_frame, out_frame):
        out_frame.data = []
        for in_data in in_frame.as_PIL():
            out_frame.data.append(in_data.transpose(PIL.Image.FLIP_TOP_BOTTOM))
        return True
