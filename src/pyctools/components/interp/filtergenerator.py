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

"""Interpolator filter generator.

Creates filters for use with Resize component. Connect 'output' to
Resize 'filter' input. Generates a new filter whenever the config
changes to allow live viewing of the effect on images.

"""

__all__ = ['FilterGenerator']

import math

from guild.actor import *
import numpy

from ...core import Component, ConfigInt

class FilterGenerator(Component):
    inputs = []

    def __init__(self):
        super(FilterGenerator, self).__init__()
        self.config['xup'] = ConfigInt(min_value=1)
        self.config['xdown'] = ConfigInt(min_value=1)
        self.config['xaperture'] = ConfigInt(min_value=1)
        self.config['yup'] = ConfigInt(min_value=1)
        self.config['ydown'] = ConfigInt(min_value=1)
        self.config['yaperture'] = ConfigInt(min_value=1)

    def process_start(self):
        super(FilterGenerator, self).process_start()
        self.gen_filter()

    def set_config(self, config):
        super(FilterGenerator, self).set_config(config)
        if self.is_alive():
            self.gen_filter()

    @actor_method
    def gen_filter(self):
        x_up = self.config['xup']
        x_down = self.config['xdown']
        x_ap = self.config['xaperture']
        y_up = self.config['yup']
        y_down = self.config['ydown']
        y_ap = self.config['yaperture']
        x_fil = self.filter_1D(x_up, x_down, x_ap)
        y_fil = self.filter_1D(y_up, y_down, y_ap)
        result = numpy.empty(y_fil.shape + x_fil.shape, dtype=numpy.float32)
        for y in range(y_fil.shape[0]):
            for x in range(x_fil.shape[0]):
                result[y, x] = x_fil[x] * y_fil[y]
        self.output(result)

    def filter_1D(self, up, down, ap):
        cut_freq = float(min(up, down)) / float(2 * up * down)
        coefs = []
        n = 1
        while True:
            theta_1 = float(n) * math.pi * 2.0 * cut_freq
            theta_2 = theta_1 * 2.0 / float(ap)
            if theta_2 >= math.pi:
                break
            coef = math.sin(theta_1) / theta_1
            win = 0.5 * (1.0 + math.cos(theta_2))
            coef = coef * win
            if abs(coef) < 1.0e-16:
                coef = 0.0
            coefs.append(coef)
            n += 1
        fil_dim = len(coefs)
        result = numpy.ones(1 + (fil_dim * 2), dtype=numpy.float32)
        n = 1
        for coef in coefs:
            result[fil_dim - n] = coef
            result[fil_dim + n] = coef
            n += 1
        # normalise gain of each phase
##        phases = (up * down) // min(up, down)
        phases = up * down
        for n in range(phases):
            result[n::phases] /= result[n::phases].sum()
        result /= float(phases)
        return result