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

from ...core import Transformer, ConfigInt
from .resizecore import resize_line

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
        self.ready = True

    def transform(self, in_frame, out_frame):
        self.update_config()
        x_up = self.config['xup']
        x_down = self.config['xdown']
        y_up = self.config['yup']
        y_down = self.config['ydown']
        in_data = in_frame.as_numpy(dtype=numpy.float32, dstack=False)
        out_frame.data = []
        for c, in_comp in enumerate(in_data):
            norm_filter = (self.filter_coefs[c % len(self.filter_coefs)] *
                           float(x_up * y_up))
            out_frame.data.append(resize_frame(
                in_comp, norm_filter, x_up, x_down, y_up, y_down))
        return True

def resize_frame(in_comp, norm_filter, x_up, x_down, y_up, y_down):
    in_shape = in_comp.shape
    ylen_in, xlen_in = in_shape[:2]
    xlen_out = (xlen_in * x_up) // x_down
    ylen_out = (ylen_in * y_up) // y_down
    xlen_out = max(xlen_out, 1)
    ylen_out = max(ylen_out, 1)
    ylen_fil, xlen_fil = norm_filter.shape
    out_comp = numpy.zeros(([ylen_out, xlen_out]), dtype=numpy.float32)
    # choice of filter coefficient is according to
    #   filter_pos = (out_pos * down) - (in_pos * up)
    # offset as filter is symmetrical
    y_fil_off = (ylen_fil - 1) // 2
    for y_out in range(ylen_out):
        y_fil_0 = -y_fil_off
        y_in_1 = min(((y_out * y_down) + y_up - y_fil_0) // y_up, ylen_in)
        y_fil_0 = (ylen_fil - 1) - y_fil_off
        y_in_0 = max(((y_out * y_down) + (y_up - 1) - y_fil_0) // y_up, 0)
        y_fil_0 = ((y_out * y_down) - (y_in_0 * y_up)) + y_fil_off
        y_fil = y_fil_0
        if x_up == 1 and x_down == 1 and xlen_fil == 1:
            # pure vertical filter
            for y_in in range(y_in_0, y_in_1):
                out_comp[y_out] += in_comp[y_in] * norm_filter[y_fil][0]
                y_fil -= y_up
        else:
            for y_in in range(y_in_0, y_in_1):
                resize_line(out_comp[y_out], in_comp[y_in],
                            norm_filter[y_fil], x_up, x_down)
                y_fil -= y_up
    return out_comp
