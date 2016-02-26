#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2015-16  Pyctools contributors
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

__all__ = ['FrameRepeat']
__docformat__ = 'restructuredtext en'

from pyctools.core.base import Component
from pyctools.core.config import ConfigInt

class FrameRepeat(Component):
    """Repeat each input frame a fixed number of times.

    This can be used to turn a still image into a video sequence, e.g.
    to help with adjusting parameters while viewing a "live" output.

    ============  ===  ====
    Config
    ============  ===  ====
    ``count``     int  Number of times to repeat each frame.
    ============  ===  ====

    """

    def initialise(self):
        self.config['count'] = ConfigInt(min_value=1)
        self.repeat_count = 0
        self.frame_no = 0

    def process_frame(self):
        self.update_config()
        count = self.config['count']
        self.repeat_count += 1
        if self.repeat_count >= count:
            self.repeat_count = 0
            in_frame = self.input_buffer['input'].get()
        else:
            in_frame = self.input_buffer['input'].peek()
        out_frame = self.outframe_pool['output'].get()
        out_frame.initialise(in_frame)
        audit = out_frame.metadata.get('audit')
        audit += 'data = FrameRepeat(data)\n'
        audit += '    count = {}\n'.format(count)
        out_frame.metadata.set('audit', audit)
        out_frame.frame_no = self.frame_no
        self.frame_no += 1
        self.send('output', out_frame)
