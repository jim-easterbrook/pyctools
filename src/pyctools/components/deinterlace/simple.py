# This file is part of pyctools http://github.com/jim-easterbrook/pyctools
# Copyright pyctools contributors
# Released under the GNU GPL3 licence

"""Simple interlace to sequential converter.

Insert lines of zero or repeat above line to convert each interlaced
frame to two sequential frames.

============  ===  ====
Config
============  ===  ====
``mode``      str  Can be set to ``insertzero`` or ``repeatline``.
``inverse``   str  Can be set to ``off`` or ``on``.
``topfirst``  str  Top field first. Can be set to ``off`` or ``on``.
============  ===  ====

"""

__all__ = ['SimpleDeinterlace']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigEnum
from pyctools.core.base import Component

class SimpleDeinterlace(Component):
    with_outframe_pool = True

    def initialise(self):
        self.config['mode'] = ConfigEnum(('insertzero', 'repeatline'))
        self.config['inverse'] = ConfigEnum(('off', 'on'))
        self.config['topfirst'] = ConfigEnum(('off', 'on'))
        self.config['topfirst'] = 'on'
        self.first_field = True

    def process_frame(self):
        self.update_config()
        repeat_line = self.config['mode'] == 'repeatline'
        top_field_first = self.config['topfirst'] == 'on'
        if self.config['inverse'] == 'on':
            self.do_inverse(top_field_first)
        else:
            self.do_forward(top_field_first, repeat_line)

    def do_forward(self, top_field_first, repeat_line):
        if self.first_field:
            in_frame = self.input_buffer['input'].peek()
            self.in_data = in_frame.as_numpy()
        else:
            in_frame = self.input_buffer['input'].get()
        out_frame = self.outframe_pool['output'].get()
        out_frame.initialise(in_frame)
        audit = out_frame.metadata.get('audit')
        audit += 'data = SimpleDeinterlace(data)\n'
        audit += '    mode: {}\n'.format(self.config['mode'])
        audit += '    topfirst: {}\n'.format(self.config['topfirst'])
        out_frame.metadata.set('audit', audit)
        out_frame.frame_no = in_frame.frame_no * 2
        out_frame.data = numpy.empty(
            self.in_data.shape, dtype=self.in_data.dtype)
        ylen = self.in_data.shape[0]
        if self.first_field == top_field_first:
            out_frame.data[0::2] = self.in_data[0::2]
            if repeat_line:
                stop = ylen - (ylen % 2)
                out_frame.data[1::2] = self.in_data[0:stop:2]
            else:
                out_frame.data[1::2] = 0
        else:
            out_frame.data[1::2] = self.in_data[1::2]
            if repeat_line:
                stop = ylen - ((ylen + 1) % 2)
                out_frame.data[0] = 0
                out_frame.data[2::2] = self.in_data[1:stop:2]
            else:
                out_frame.data[0::2] = 0
        if not self.first_field:
            out_frame.frame_no += 1
        self.output(out_frame)
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
        audit += 'data = SimpleReinterlace(data)\n'
        audit += '    topfirst: {}\n'.format(self.config['topfirst'])
        out_frame.metadata.set('audit', audit)
        out_frame.frame_no = in_frame.frame_no // 2
        out_frame.data = numpy.empty(
            second_field_data.shape, dtype=second_field_data.dtype)
        if top_field_first:
            out_frame.data[0::2] = self.first_field_data[0::2]
            out_frame.data[1::2] = second_field_data[1::2]
        else:
            out_frame.data[1::2] = self.first_field_data[1::2]
            out_frame.data[0::2] = second_field_data[0::2]
        self.output(out_frame)
        self.first_field = not self.first_field
