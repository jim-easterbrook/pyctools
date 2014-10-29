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
from .zoneplategeneratorcore import zone_frame

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
        k0  = self.config['k0']
        kx  = self.config['kx']
        ky  = self.config['ky']
        kt  = self.config['kt']
        kx2 = self.config['kx2']
        kxy = self.config['kxy']
        kxt = self.config['kxt']
        kyx = self.config['kyx']
        ky2 = self.config['ky2']
        kyt = self.config['kyt']
        ktx = self.config['ktx']
        kty = self.config['kty']
        kt2 = self.config['kt2']
        frame.metadata.copy(self.metadata)
        audit = frame.metadata.get('audit')
        audit += 'data = ZonePlateGenerator()\n'
        audit += '    '
        if k0 != 0.0:
            audit += 'k0: %g, ' % k0
        if kx != 0.0:
            audit += 'kx: %g, ' % kx
        if ky != 0.0:
            audit += 'ky: %g, ' % ky
        if kt != 0.0:
            audit += 'kt: %g, ' % kt
        if kx2 != 0.0:
            audit += 'kx2: %g, ' % kx2
        if kxy != 0.0:
            audit += 'kxy: %g, ' % kxy
        if kxt != 0.0:
            audit += 'kxt: %g, ' % kxt
        if kyx != 0.0:
            audit += 'kyx: %g, ' % kyx
        if ky2 != 0.0:
            audit += 'ky2: %g, ' % ky2
        if kyt != 0.0:
            audit += 'kyt: %g, ' % kyt
        if ktx != 0.0:
            audit += 'ktx: %g, ' % ktx
        if kty != 0.0:
            audit += 'kty: %g, ' % kty
        if kt2 != 0.0:
            audit += 'kt2: %g, ' % kt2
        audit += 'xlen: %d, ylen: %d, zlen: %d\n' % (xlen, ylen, zlen)
        frame.metadata.set('audit', audit)
        k0 =        k0  * self.phases
        kx =        kx  * self.phases
        ky = (1.0 - ky) * self.phases
        kt =        kt  * self.phases
        kx2 =       kx2 * self.phases / float(xlen)
        kxy =      -kxy * self.phases / float(ylen)
        kxt =       kxt * self.phases / float(zlen)
        kyx =      -kyx * self.phases / float(xlen)
        ky2 =       ky2 * self.phases / float(ylen)
        kyt =      -kyt * self.phases / float(zlen)
        ktx =       ktx * self.phases / float(xlen)
        kty =      -kty * self.phases / float(ylen)
        kt2 =       kt2 * self.phases / float(zlen)
        # generate this frame
        data = numpy.ndarray([ylen, xlen], dtype=numpy.float32)
        zone_frame(data, self.waveform, self.frame_no % zlen,
                   k0, kx, ky, kt, kx2, kxy, kxt, kyx, ky2, kyt, ktx, kty, kt2)
        # set output frame
        frame.data = [data]
        frame.type = self.frame_type
        frame.frame_no = self.frame_no
        self.frame_no += 1
        self.output(frame)
