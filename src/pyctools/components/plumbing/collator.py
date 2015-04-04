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

"""Merge two inputs to produce a set of co-timed frames.

This component allows two components' outputs to be merged. The inputs
must be :py:class:`~pyctools.core.frame.Frame` objects -- the frame
numbers are used to ensure that only co-timed frames are merged.

"""

__all__ = ['Collator']

import numpy

from pyctools.core.base import Component

class Collator(Component):
    inputs = ['input1', 'input2']

    def initialise(self):
        self.logger.warning('Deprecation warning: Collator is no longer required')

    def process_frame(self):
        in_frame1 = self.input_buffer['input1'].get()
        in_frame2 = self.input_buffer['input2'].get()
        out_frame = self.outframe_pool['output'].get()
        out_frame.initialise(in_frame1)
        audit = 'input1 = {\n%s}\n' % in_frame1.metadata.get('audit')
        audit += 'input2 = {\n%s}\n' % in_frame2.metadata.get('audit')
        audit += 'data = [input1, input2]\n'
        out_frame.metadata.set('audit', audit)
        out_frame.data = numpy.concatenate(
            (in_frame1.as_numpy(), in_frame2.as_numpy()), axis=2)
        self.send('output', out_frame)
