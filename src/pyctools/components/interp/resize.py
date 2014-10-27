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

    def __init__(self):
        super(Resize, self).__init__()
        self.config['xup'] = ConfigInt(min_value=1)
        self.config['xdown'] = ConfigInt(min_value=1)
        self.config['yup'] = ConfigInt(min_value=1)
        self.config['ydown'] = ConfigInt(min_value=1)
        self.ready = False

    @actor_method
    def filter(self, new_filter):
        if not isinstance(new_filter, (list, tuple)):
            self.logger.warning('Filter input must be a list of numpy arrays')
            return
        for filt in new_filter:
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
        self.ready = True

    def transform(self, in_frame, out_frame):
        self.update_config()
        x_up = self.config['xup']
        x_down = self.config['xdown']
        y_up = self.config['yup']
        y_down = self.config['ydown']
        in_data = in_frame.as_numpy(dtype=numpy.float32, dstack=False)
        if self.fil_count != len(self.filter_coefs):
            self.fil_count = len(self.filter_coefs)
            if self.fil_count != 1 and self.fil_count != len(in_data):
                self.logger.warning('Mismatch between %d filters and %d images',
                                    self.fil_count, len(in_data))
        out_frame.data = []
        for c, in_comp in enumerate(in_data):
            norm_filter = (
                self.filter_coefs[c % self.fil_count] * float(x_up * y_up))
            out_frame.data.append(resize_frame(
                in_comp, norm_filter, x_up, x_down, y_up, y_down))
        return True
