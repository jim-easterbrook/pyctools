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

"""Half-sizing interlace to sequential converter.

"""

__all__ = ['HalfSize']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigEnum
from pyctools.core.base import Component
from pyctools.core.types import pt_float

class HalfSize(Component):
    with_outframe_pool = True

    def initialise(self):
        self.config['inverse'] = ConfigEnum(('off', 'on'))
        self.first_field = True

    def process_frame(self):
        self.update_config()
        if self.config['inverse'] == 'on':
            self.do_inverse()
        else:
            self.do_forward()

    def do_forward(self):
        if self.first_field:
            in_frame = self.input_buffer['input'].peek()
        else:
            in_frame = self.input_buffer['input'].get()
        out_frame = self.outframe_pool['output'].get()
        out_frame.initialise(in_frame)
        in_data = in_frame.as_numpy()
        audit = out_frame.metadata.get('audit')
        audit += 'data = HalfSizeDeinterlace(data)\n'
        out_frame.metadata.set('audit', audit)
        out_frame.frame_no = in_frame.frame_no * 2
        if self.first_field:
            out_frame.data = in_data[0::2]
        else:
            out_frame.data = in_data[1::2]
            out_frame.frame_no += 1
        self.output(out_frame)
        self.first_field = not self.first_field

    def do_inverse(self):
        in_frame = self.input_buffer['input'].get()
        if self.first_field:
            self.first_field_data = in_frame.as_numpy()
            self.first_field = not self.first_field
            return
        out_frame = self.outframe_pool['output'].get()
        out_frame.initialise(in_frame)
        second_field_data = in_frame.as_numpy()
        audit = out_frame.metadata.get('audit')
        audit += 'data = HalfSizeReinterlace(data)\n'
        out_frame.metadata.set('audit', audit)
        out_frame.frame_no = in_frame.frame_no // 2
        out_frame.data = numpy.empty(
            [self.first_field_data.shape[0] + second_field_data.shape[0]] +
            list(second_field_data.shape[1:]), dtype=second_field_data.dtype)
        out_frame.data[0::2] = self.first_field_data
        out_frame.data[1::2] = second_field_data
        self.output(out_frame)
        self.first_field = not self.first_field
