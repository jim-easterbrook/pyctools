#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-15  Pyctools contributors
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

"""Subtract second input from first.

"""

__all__ = ['Subtracter']

from pyctools.core.base import Component

class Subtracter(Component):
    inputs = ['input0', 'input1']

    def process_frame(self):
        in_frame1 = self.input_buffer['input0'].get()
        in_frame2 = self.input_buffer['input1'].get()
        out_frame = self.outframe_pool['output'].get()
        out_frame.initialise(in_frame1)
        audit = 'input0 = {\n%s}\n' % in_frame1.metadata.get('audit')
        audit += 'input1 = {\n%s}\n' % in_frame2.metadata.get('audit')
        audit += 'data = input0 - input1\n'
        out_frame.metadata.set('audit', audit)
        out_frame.data = in_frame1.as_numpy() - in_frame2.as_numpy()
        self.send('output', out_frame)
