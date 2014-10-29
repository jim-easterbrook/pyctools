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

"""Extract colour components.

Extract one or more components from a multi-component (RGB, YCrCb,
etc.) input.

"""

__all__ = ['ExtractComps']

from pyctools.core import Transformer, ConfigInt

class ExtractComps(Transformer):
    def initialise(self):
        self.config['start'] = ConfigInt(min_value=0)
        self.config['end'] = ConfigInt(min_value=1)

    def transform(self, in_frame, out_frame):
        self.update_config()
        start = self.config['start']
        end = self.config['end']
        in_data = in_frame.as_numpy()
        if len(in_data) > 1:
            out_frame.data = in_data[start:end]
        else:
            out_frame.data = [in_data[0][:,:,start:end]]
        audit = out_frame.metadata.get('audit')
        audit += 'data = data[%d:%d]\n' % (start, end)
        out_frame.metadata.set('audit', audit)
        return True
