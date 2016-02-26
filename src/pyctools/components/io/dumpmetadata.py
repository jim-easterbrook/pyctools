#!/usr/bin/env python
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

from __future__ import print_function

__all__ = ['DumpMetadata']
__docformat__ = 'restructuredtext en'

import pprint

from pyctools.core.base import Transformer
from pyctools.core.config import ConfigBool

class DumpMetadata(Transformer):
    """Print input frames' metadata.

    This is a "pass through" component that can be inserted anywhere in
    a pipeline. It prints (to :py:obj:`sys.stdout`) the metadata "audit
    trail" of its input frames.

    Note that the audit trail is only printed out for the first frame
    and if it subsequently changes.

    """

    def initialise(self):
        self.config['raw'] = ConfigBool()
        self.last_metadata = None

    def transform(self, in_frame, out_frame):
        if self.update_config():
            self.last_metadata = None
        if self.last_metadata and in_frame.metadata.data == self.last_metadata.data:
            return True
        self.last_metadata = in_frame.metadata
        print('Frame %04d' % in_frame.frame_no)
        print('==========')
        if self.config['raw']:
            pprint.pprint(in_frame.metadata.data)
        else:
            indent = 0
            for line in in_frame.metadata.get('audit').splitlines():
                print(' ' * indent, line)
                if '{' in line:
                    indent += 8
                if '}' in line:
                    indent -= 8
        return True
