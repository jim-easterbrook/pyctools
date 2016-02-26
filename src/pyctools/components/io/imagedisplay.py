#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-16  Pyctools contributors
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

import PIL.Image

__all__ = ['ImageDisplay']
__docformat__ = 'restructuredtext en'

from pyctools.core.base import Transformer

class ImageDisplay(Transformer):
    """View still image file.

    This is a "pass through" component that can be inserted anywhere in a
    pipeline. It displays the first frame it receives using
    :py:meth:`PIL.Image.Image.show`.

    """

    def initialise(self):
        self.done = False

    def transform(self, in_frame, out_frame):
        if self.done:
            return True
        image = in_frame.as_PIL()
        image.show()
        self.done = True
        return True
