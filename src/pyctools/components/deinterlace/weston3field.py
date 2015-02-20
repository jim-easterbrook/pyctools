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

"""'Weston 3-field' interlace to sequential converter.

============  ===  ====
Config
============  ===  ====
``mode``      int  Filtering mode. Can be set to ``0`` or ``1``.
``topfirst``  str  Top field first. Can be set to ``off`` or ``on``.
============  ===  ====

"""

__all__ = ['Weston3Field']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.components.interp.resize import resize_frame
from pyctools.core.config import ConfigEnum, ConfigInt
from pyctools.core.base import Component
from pyctools.core.types import pt_float

class Weston3Field(Component):
    with_outframe_pool = True
    coef_lf = {
        0: numpy.array([32768, 0, 32768],
                       dtype=pt_float).reshape(-1, 1, 1) / pt_float(2**16),
        1: numpy.array([-1704, 0, 34472, 0, 34472, 0, -1704],
                       dtype=pt_float).reshape(-1, 1, 1) / pt_float(2**16),
        }
    coef_hf = {
        0: numpy.array([-4096, 0, 8192, 0, -4096],
                       dtype=pt_float).reshape(-1, 1, 1) / pt_float(2**16),
        1: numpy.array([2032, 0, -7602, 0, 11140, 0, -7602, 0, 2032],
                       dtype=pt_float).reshape(-1, 1, 1) / pt_float(2**16),
        }

    def initialise(self):
        self.config['mode'] = ConfigInt(min_value=0, max_value=1)
        self.config['topfirst'] = ConfigEnum(('off', 'on'))
        self.config['topfirst'] = 'on'
        self.first_field = True
        self.prev_hf = None
        self.delayed_frame = None

    def process_frame(self):
        self.update_config()
        mode = self.config['mode']
        top_field_first = self.config['topfirst'] == 'on'
        if self.first_field:
            in_frame = self.input_buffer['input'].peek()
            self.in_data = in_frame.as_numpy(dtype=pt_float)
            self.lf_data = resize_frame(
                self.in_data, self.coef_lf[mode], 1, 1, 1, 1)
            self.hf_data = resize_frame(
                self.in_data, self.coef_hf[mode], 1, 1, 1, 1)
        else:
            in_frame = self.input_buffer['input'].get()
        if top_field_first == self.first_field:
            top_line = 0
        else:
            top_line = 1
        if self.delayed_frame:
            # complete last frame with hf from first field of this frame
            self.delayed_frame.data[top_line::2] += self.hf_data[top_line::2]
            self.output(self.delayed_frame)
            self.delayed_frame = None
        out_frame = self.outframe_pool['output'].get()
        out_frame.initialise(in_frame)
        audit = out_frame.metadata.get('audit')
        audit += 'data = Weston3FieldDeinterlace(data)\n'
        out_frame.metadata.set('audit', audit)
        out_frame.frame_no = in_frame.frame_no * 2
        out_frame.data = numpy.empty(
            self.in_data.shape, dtype=self.in_data.dtype)
        out_frame.data[top_line::2] = self.in_data[top_line::2]
        out_frame.data[1-top_line::2] = (
            self.lf_data[1-top_line::2] + self.hf_data[1-top_line::2])
        if self.first_field:
            if self.prev_hf is not None:
                out_frame.data[1-top_line::2] += self.prev_hf[1-top_line::2]
            self.output(out_frame)
            self.prev_hf = self.hf_data
        else:
            out_frame.frame_no += 1
            self.delayed_frame = out_frame
        self.first_field = not self.first_field

    def onStop(self):
        if self.delayed_frame:
            # send last frame before stopping
            self.output(self.delayed_frame)
            self.delayed_frame = None
        super(Weston3Field, self).onStop()