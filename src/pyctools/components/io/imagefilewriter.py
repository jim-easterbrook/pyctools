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

"""Save still image file.

This is a "pass through" component that can be inserted anywhere in a
pipeline. It saves the first frame it receives to file using
:py:meth:`PIL.Image.Image.save`.

"""

import PIL.Image

__all__ = ['ImageFileWriter']
__docformat__ = 'restructuredtext en'

from pyctools.core.config import ConfigPath
from pyctools.core.frame import Metadata
from pyctools.core.base import Transformer

class ImageFileWriter(Transformer):
    def initialise(self):
        self.done = False
        self.config['path'] = ConfigPath()

    def transform(self, in_frame, out_frame):
        if self.done:
            return True
        self.update_config()
        path = self.config['path']
        image = in_frame.as_PIL()
        if len(image) == 1:
            image = image[0]
        else:
            image = PIL.Image.merge(in_frame.type, image)
        image.save(path)
        md = Metadata().copy(in_frame.metadata)
        audit = md.get('audit')
        audit += '%s = data\n' % path
        md.set('audit', audit)
        md.to_file(path)
        self.done = True
        return True
