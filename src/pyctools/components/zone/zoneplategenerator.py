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

"""Raw file reader.

"""

__all__ = ['ZonePlateGenerator']

import math
import sys

from guild.actor import *
import numpy

from ...core import Metadata, Component, ConfigFloat, ConfigInt, ConfigEnum
from ...extensions.zone import zone_frame

class ZonePlateGenerator(Component):
    inputs = []

    def __init__(self):
        super(ZonePlateGenerator, self).__init__(with_outframe_pool=True)
        self.config['k0'] = ConfigFloat(
            value=0.0, min_value=0.0, max_value=1.0, decimals=2,
            wrapping=True, dynamic=True)
        self.config['kx'] = ConfigFloat(
            value=0.0, min_value=0.0, max_value=1.0, decimals=2,
            wrapping=True, dynamic=True)
        self.config['ky'] = ConfigFloat(
            value=0.0, min_value=0.0, max_value=1.0, decimals=2,
            wrapping=True, dynamic=True)
        self.config['kt'] = ConfigFloat(
            value=0.0, min_value=0.0, max_value=1.0, decimals=2,
            wrapping=True, dynamic=True)
        self.config['kx2'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=2,
            wrapping=True, dynamic=True)
        self.config['kxy'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=2,
            wrapping=True, dynamic=True)
        self.config['kxt'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=2,
            wrapping=True, dynamic=True)
        self.config['kyx'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=2,
            wrapping=True, dynamic=True)
        self.config['ky2'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=2,
            wrapping=True, dynamic=True)
        self.config['kyt'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=2,
            wrapping=True, dynamic=True)
        self.config['ktx'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=2,
            wrapping=True, dynamic=True)
        self.config['kty'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=2,
            wrapping=True, dynamic=True)
        self.config['kt2'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=2,
            wrapping=True, dynamic=True)
        self.config['xlen'] = ConfigInt(value=720, min_value=1, dynamic=True)
        self.config['ylen'] = ConfigInt(value=576, min_value=1, dynamic=True)
        self.config['zlen'] = ConfigInt(value=32, min_value=1, dynamic=True)
        self.config['looping'] = ConfigEnum(('off', 'repeat'), dynamic=True)

    def process_start(self):
        super(ZonePlateGenerator, self).process_start()
        # store sine wave in a lookup table
        self.phases = 1024
        self.waveform = numpy.ndarray([self.phases], dtype=numpy.float32)
        for i in range(self.phases):
            phase = float(i) / float(self.phases)
            self.waveform[i] = 16.0 + (
                219.0 * (1.0 + math.cos(phase * math.pi * 2.0)) / 2.0)
        self.metadata = Metadata()
        self.frame_type = 'Y'
        self.frame_no = 0
        self.update_config()
        k0 = self.config['k0']
        kx = self.config['kx']
        ky = 1.0 - self.config['ky']
        kt = self.config['kt']
        self.Iktdt_k0 = k0 * self.phases
        self.Ikt2dt_kt = kt * self.phases
        self.Ikxtdt_kx = kx * self.phases
        self.Ikytdt_ky = ky * self.phases

    @actor_method
    def new_out_frame(self, frame):
        self.update_config()
        xlen = self.config['xlen']
        ylen = self.config['ylen']
        zlen = self.config['zlen']
        if self.frame_no >= zlen and self.config['looping'] == 'off':
            self.output(None)
            self.stop()
            return
        data = numpy.ndarray([ylen, xlen], dtype=numpy.float32)
        kx2 =  self.config['kx2'] * self.phases / float(xlen)
        kxy = -self.config['kxy'] * self.phases / float(ylen)
        kxt =  self.config['kxt'] * self.phases / float(zlen)
        kyx = -self.config['kyx'] * self.phases / float(xlen)
        ky2 =  self.config['ky2'] * self.phases / float(ylen)
        kyt = -self.config['kyt'] * self.phases / float(zlen)
        ktx =  self.config['ktx'] * self.phases / float(xlen)
        kty = -self.config['kty'] * self.phases / float(ylen)
        kt2 =  self.config['kt2'] * self.phases / float(zlen)
        # initialise vertical integrals
        Ikydy_Iktdt_k0 = self.Iktdt_k0
        Iky2dy_Ikytdt_ky = self.Ikytdt_ky
        Ikxydy_Ikxtdt_kx = self.Ikxtdt_kx
        # generate this frame
        zone_frame(data, self.waveform, kx2, kxy, kyx, ky2,
                   self.Iktdt_k0, self.Ikytdt_ky, self.Ikxtdt_kx)
        # increment temporal integrals
        self.Iktdt_k0 = (self.Iktdt_k0 + self.Ikt2dt_kt) % self.phases
        self.Ikt2dt_kt = (self.Ikt2dt_kt + kt2) % self.phases
        self.Ikxtdt_kx = (self.Ikxtdt_kx + kxt + ktx) % self.phases
        self.Ikytdt_ky = (self.Ikytdt_ky + kyt + kty) % self.phases
        # set output frame
        frame.data = [data]
        frame.type = self.frame_type
        frame.frame_no = self.frame_no
        self.frame_no += 1
        frame.metadata.copy(self.metadata)
        self.output(frame)
