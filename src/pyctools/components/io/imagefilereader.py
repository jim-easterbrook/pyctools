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

"""Read still image file (jpg, png, ppm, etc.).

===========  ===  ====
Config
===========  ===  ====
``path``     str  Path name of file to be read.
===========  ===  ====

"""

from __future__ import print_function

__all__ = ['ImageFileReader']
__docformat__ = 'restructuredtext en'

import time

import PIL.Image

from pyctools.core.config import ConfigPath
from pyctools.core.base import Component
from pyctools.core.frame import Frame

class ImageFileReader(Component):
    inputs = []

    def initialise(self):
        self.config['path'] = ConfigPath()

    def gen_process(self):
        # wait for self.output to be connected
        while self.output.__self__ == self:
            yield 1
            time.sleep(0.01)
        # read file
        self.update_config()
        path = self.config['path']
        out_frame = Frame()
        image = PIL.Image.open(path)
        # send output frame
        out_frame.data = [image]
        out_frame.type = image.mode
        out_frame.frame_no = 0
        out_frame.metadata.from_file(path)
        audit = out_frame.metadata.get('audit')
        audit += 'data = %s\n' % path
        out_frame.metadata.set('audit', audit)
        self.output(out_frame)
        # shut down pipeline
        self.output(None)
        self.stop()
