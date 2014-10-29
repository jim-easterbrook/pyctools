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

"""Interpolating image resizer.

Resize an image using a user supplied filter. If no filter is supplied
then "nearest pixel" interpolation is used.

"""

__all__ = ['Resize']

from guild.actor import *
import numpy

from pyctools.core import Transformer, ConfigInt
from .resizecore import resize_frame

class Resize(Transformer):
    inputs = ['input', 'filter']

    def initialise(self):
        self.config['xup'] = ConfigInt(min_value=1)
        self.config['xdown'] = ConfigInt(min_value=1)
        self.config['yup'] = ConfigInt(min_value=1)
        self.config['ydown'] = ConfigInt(min_value=1)
        self.set_ready(False)

    @actor_method
    def filter(self, new_filter):
        for filt in new_filter.data:
            if not isinstance(filt, numpy.ndarray):
                self.logger.warning('Each filter input must be a numpy array')
                return
            if filt.ndim != 2:
                self.logger.warning('Each filter input must be 2 dimensional')
                return
            ylen, xlen = filt.shape
            if (xlen % 2) != 1 or (ylen % 2) != 1:
                self.logger.warning('Each filter input must have odd dimensions')
                return
        self.filter_coefs = new_filter
        self.fil_count = None
        self.set_ready(True)

    def transform(self, in_frame, out_frame):
        self.update_config()
        x_up = self.config['xup']
        x_down = self.config['xdown']
        y_up = self.config['yup']
        y_down = self.config['ydown']
        in_data = in_frame.as_numpy(dtype=numpy.float32, dstack=False)
        if self.fil_count != len(self.filter_coefs.data):
            self.fil_count = len(self.filter_coefs.data)
            if self.fil_count != 1 and self.fil_count != len(in_data):
                self.logger.warning('Mismatch between %d filters and %d images',
                                    self.fil_count, len(in_data))
        out_frame.data = []
        for c, in_comp in enumerate(in_data):
            norm_filter = (
                self.filter_coefs.data[c % self.fil_count] * float(x_up * y_up))
            out_frame.data.append(resize_frame(
                in_comp, norm_filter, x_up, x_down, y_up, y_down))
        audit = out_frame.metadata.get('audit')
        audit += 'data = Resize(data)\n'
        if x_up != 1 or x_down != 1:
            audit += '    x_up: %d, x_down: %d\n' % (x_up, x_down)
        if y_up != 1 or y_down != 1:
            audit += '    y_up: %d, y_down: %d\n' % (y_up, y_down)
        audit += '    filter: {\n%s}\n' % (
            self.filter_coefs.metadata.get('audit'))
        out_frame.metadata.set('audit', audit)
        return True
