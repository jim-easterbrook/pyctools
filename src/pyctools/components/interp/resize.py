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
from ...extensions.resize import resize_line1, resize_line2

class Resize(Transformer):
    inputs = ['input', 'filter']

    def __init__(self):
        super(Resize, self).__init__()
        self.config['xup'] = ConfigInt(min_value=1)
        self.config['xdown'] = ConfigInt(min_value=1)
        self.config['yup'] = ConfigInt(min_value=1)
        self.config['ydown'] = ConfigInt(min_value=1)

    def process_start(self):
        super(Resize, self).process_start()
        self.update_config()
        # make simple "nearest pixel" filter
        xup = self.config['xup']
        yup = self.config['yup']
        xlen = xup
        ylen = yup
        if (xlen % 2) != 1:
            xlen += 1
        if (ylen % 2) != 1:
            ylen += 1
        self.filter_coefs = numpy.zeros((ylen, xlen), dtype=numpy.float32)
        self.filter_coefs[0:yup, 0:xup] = 1.0 / float(xup * yup)

    @actor_method
    def filter(self, new_filter):
        if not isinstance(new_filter, numpy.ndarray):
            self.logger.warning('Filter input must be a numpy array')
            return
        if new_filter.ndim != 2:
            self.logger.warning('Filter input must be 2 dimensional')
            return
        ylen, xlen = new_filter.shape
        if (xlen % 2) != 1 or (ylen % 2) != 1:
            self.logger.warning('Filter input must have odd dimensions')
            return
        self.filter_coefs = new_filter

    def transform(self, in_frame, out_frame):
        self.update_config()
        x_up = self.config['xup']
        x_down = self.config['xdown']
        y_up = self.config['yup']
        y_down = self.config['ydown']
        in_data = in_frame.as_numpy()
        norm_filter = self.filter_coefs * float(x_up * y_up)
        out_frame.data = []
        for in_comp in in_data:
            out_frame.data.append(resize_frame(
                in_comp.astype(numpy.float32), norm_filter,
                x_up, x_down, y_up, y_down))
        return True

def resize_frame(in_comp, norm_filter, x_up, x_down, y_up, y_down):
    in_shape = in_comp.shape
    ylen_in, xlen_in = in_shape[:2]
    xlen_out = (xlen_in * x_up) // x_down
    ylen_out = (ylen_in * y_up) // y_down
    xlen_out = max(xlen_out, 1)
    ylen_out = max(ylen_out, 1)
    ylen_fil, xlen_fil = norm_filter.shape
    out_comp = numpy.zeros(
        [ylen_out, xlen_out] + list(in_shape[2:]), dtype=numpy.float32)
    # choice of filter coefficient is according to
    #   filter_pos = (out_pos * down) - (in_pos * up)
    # save computation by using increments and decrements
    # on each loop iteration
    dy_in = 1 + ((y_down - 1) // y_up)
    dy_fil = y_down - (dy_in * y_up)
    y_in_0 = 0
    y_fil_0 = (ylen_fil - 1) // 2
    while y_fil_0 >= y_up and y_in_0 < ylen_in - 1:
        y_fil_0 -= y_up
        y_in_0 += 1
    for y_out in range(ylen_out):
        y_fil_1 = min(ylen_fil, y_fil_0 + (y_in_0 * y_up) + 1)
        y_in = y_in_0
        for y_fil in range(y_fil_0, y_fil_1, y_up):
            if in_comp.ndim == 2:
                resize_line1(out_comp[y_out], in_comp[y_in],
                             norm_filter[y_fil], x_up, x_down)
            else:
                resize_line2(out_comp[y_out], in_comp[y_in],
                             norm_filter[y_fil], x_up, x_down)
            y_in -= 1
        y_fil_0 += dy_fil
        y_in_0 += dy_in
        while y_fil_0 < 0 or y_in_0 >= ylen_in:
            y_fil_0 += y_up
            y_in_0 -= 1
    return out_comp
