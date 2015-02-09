#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2015  Jim Easterbrook  jim@jim-easterbrook.me.uk
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

"""Zero-inserting interlace to sequential converter.

This simply rearranges each interlaced frame into two frames where half
the lines in each are filled with zero. It can be used for viewing
pictures directly but you probably want to follow it with a suitable
filter.

============  ===  ====
Config
============  ===  ====
``topfirst``  str  Top field first. Can be set to ``off`` or ``on``.
============  ===  ====

"""

__all__ = ['InsertZero']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigEnum
from pyctools.core.base import Component
from pyctools.core.types import pt_float

class InsertZero(Component):
    with_outframe_pool = True

    def initialise(self):
        self.config['topfirst'] = ConfigEnum(('off', 'on'))
        self.config['topfirst'] = 'on'
        self.first_field = True

    def process_frame(self):
        self.update_config()
        top_field_first = self.config['topfirst'] == 'on'
        if self.first_field:
            in_frame = self.input_buffer['input'].peek()
        else:
            in_frame = self.input_buffer['input'].get()
        out_frame = self.outframe_pool['output'].get()
        out_frame.initialise(in_frame)
        self.in_data = in_frame.as_numpy()
        audit = out_frame.metadata.get('audit')
        audit += 'data = InsertZeroDeinterlace(data)\n'
        out_frame.metadata.set('audit', audit)
        out_frame.frame_no = in_frame.frame_no * 2
        out_frame.data = numpy.zeros(self.in_data.shape, dtype=pt_float)
        if self.first_field == top_field_first:
            out_frame.data[0::2] = self.in_data[0::2]
        else:
            out_frame.data[1::2] = self.in_data[1::2]
        if not self.first_field:
            out_frame.frame_no += 1
        self.output(out_frame)
        self.first_field = not self.first_field
