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
        self.metadata = Metadata()
        self.frame_type = 'Y'
        self.frame_no = 0
        k0 = self.config['k0']
        kx = self.config['kx']
        ky = 1.0 - self.config['ky']
        kt = self.config['kt']
        self.Iktdt_k0 = k0
        self.Ikt2dt_kt = kt
        self.Ikxtdt_kx = kx
        self.Ikytdt_ky = ky

    @actor_method
    def new_out_frame(self, frame):
        xlen = self.config['xlen']
        ylen = self.config['ylen']
        zlen = self.config['zlen']
        if self.frame_no >= zlen and self.config['looping'] == 'off':
            self.output(None)
            self.stop()
            return
        data = numpy.ndarray([ylen, xlen], dtype=numpy.float32)
        kx2 =  self.config['kx2'] / float(xlen)
        kxy = -self.config['kxy'] / float(ylen)
        kxt =  self.config['kxt'] / float(zlen)
        kyx = -self.config['kyx'] / float(xlen)
        ky2 =  self.config['ky2'] / float(ylen)
        kyt = -self.config['kyt'] / float(zlen)
        ktx =  self.config['ktx'] / float(xlen)
        kty = -self.config['kty'] / float(ylen)
        kt2 =  self.config['kt2'] / float(zlen)
        # initialise vertical integrals
        Ikydy_Iktdt_k0 = self.Iktdt_k0
        Iky2dy_Ikytdt_ky = self.Ikytdt_ky
        Ikxydy_Ikxtdt_kx = self.Ikxtdt_kx
        for y in range(ylen):
            # initialise horizontal integrals
            Ikxdx_Ikydy_Iktdt_k0 = Ikydy_Iktdt_k0
            Ikx2dx_Ikxydy_Ikxtdt_kx = Ikxydy_Ikxtdt_kx
            for x in range(xlen):
                phase = Ikxdx_Ikydy_Iktdt_k0 % 1.0
                # compute sine here
                data[y, x] = 16.0 + (219.0 * (1.0 + math.cos(phase * math.pi * 2.0)) / 2.0)
                # increment horizontal integrals
                Ikxdx_Ikydy_Iktdt_k0 = (Ikxdx_Ikydy_Iktdt_k0 + Ikx2dx_Ikxydy_Ikxtdt_kx) % 1.0
                Ikx2dx_Ikxydy_Ikxtdt_kx = (Ikx2dx_Ikxydy_Ikxtdt_kx + kx2) % 1.0
            # increment vertical integrals
            Ikydy_Iktdt_k0 = (Ikydy_Iktdt_k0 + Iky2dy_Ikytdt_ky) % 1.0
            Iky2dy_Ikytdt_ky = (Iky2dy_Ikytdt_ky + ky2) % 1.0
            Ikxydy_Ikxtdt_kx = (Ikxydy_Ikxtdt_kx + kxy + kyx) % 1.0
        # increment temporal integrals
        self.Iktdt_k0 = (self.Iktdt_k0 + self.Ikt2dt_kt) % 1.0
        self.Ikt2dt_kt = (self.Ikt2dt_kt + kt2) % 1.0
        self.Ikxtdt_kx = (self.Ikxtdt_kx + kxt + ktx) % 1.0
        self.Ikytdt_ky = (self.Ikytdt_ky + kyt + kty) % 1.0
        # convert to numpy arrays
        frame.data = [data]
        frame.type = self.frame_type
        frame.frame_no = self.frame_no
        self.frame_no += 1
        frame.metadata.copy(self.metadata)
        self.output(frame)
