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

__all__ = ['ExtractComps']
__docformat__ = 'restructuredtext en'

from pyctools.core.config import ConfigInt
from pyctools.core.base import Transformer

class ExtractComps(Transformer):
    """Extract colour components.

    Extract one or more components from a multi-component (RGB, YCrCb,
    etc.) input. The output components are specified by the config items
    ``start`` and ``stop``. As in a Python :py:class:`slice`, ``stop``
    should be one more than the last component required.

    Note that this operation is just as easily done with an
    :py:class:`~pyctools.components.arithmetic.Arithmetic` component::

        extract_R = Arithmetic(func='data[:,:,0:1]')
        extract_G = Arithmetic(func='data[:,:,1:2]')
        extract_B = Arithmetic(func='data[:,:,2:3]')

    """

    def initialise(self):
        self.config['start'] = ConfigInt(min_value=0)
        self.config['stop'] = ConfigInt(min_value=1)

    def transform(self, in_frame, out_frame):
        self.update_config()
        start = self.config['start']
        stop = self.config['stop']
        in_data = in_frame.as_numpy()
        out_frame.data = in_data[:,:,start:stop]
        audit = out_frame.metadata.get('audit')
        audit += 'data = data[:,:,{}:{}]\n'.format(start, stop)
        out_frame.metadata.set('audit', audit)
        return True
