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

__all__ = ['HalfSize']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigBool
from pyctools.core.base import Component

class HalfSize(Component):
    """Half-sizing interlace to sequential converter.

    This simply rearranges each interlaced frame into two frames of half
    the height. It is no use for viewing pictures but is useful if you
    want to do some spatial processing, e.g. taking a Fourier transform.

    In ``inverse`` mode pairs of half-height frames are reassembled into
    single full height frames.

    ============  ====  ====
    Config
    ============  ====  ====
    ``inverse``   bool
    ``topfirst``  bool  Top field first.
    ============  ====  ====

    """

    def initialise(self):
        self.config['inverse'] = ConfigBool()
        self.config['topfirst'] = ConfigBool(value=True)
        self.first_field = True

    def process_frame(self):
        self.update_config()
        if self.config['inverse']:
            self.do_inverse(self.config['topfirst'])
        else:
            self.do_forward(self.config['topfirst'])

    def do_forward(self, top_field_first):
        if self.first_field:
            in_frame = self.input_buffer['input'].peek()
            self.in_data = in_frame.as_numpy()
        else:
            in_frame = self.input_buffer['input'].get()
        out_frame = self.outframe_pool['output'].get()
        out_frame.initialise(in_frame)
        audit = out_frame.metadata.get('audit')
        audit += 'data = HalfSizeDeinterlace(data)\n'
        out_frame.metadata.set('audit', audit)
        out_frame.frame_no = in_frame.frame_no * 2
        if self.first_field == top_field_first:
            out_frame.data = self.in_data[0::2]
        else:
            out_frame.data = self.in_data[1::2]
        if not self.first_field:
            out_frame.frame_no += 1
        self.send('output', out_frame)
        self.first_field = not self.first_field

    def do_inverse(self, top_field_first):
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
        if top_field_first:
            out_frame.data[0::2] = self.first_field_data
            out_frame.data[1::2] = second_field_data
        else:
            out_frame.data[1::2] = self.first_field_data
            out_frame.data[0::2] = second_field_data
        self.send('output', out_frame)
        self.first_field = not self.first_field
