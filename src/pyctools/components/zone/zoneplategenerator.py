#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-18  Pyctools contributors
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

__all__ = ['ZonePlateGenerator']
__docformat__ = 'restructuredtext en'

import math
import sys

import numpy

from pyctools.core.base import Component
from pyctools.core.config import ConfigFloat, ConfigInt, ConfigEnum
from .zoneplategeneratorcore import zone_frame

class ZonePlateGenerator(Component):
    """Zone plate test pattern generator.

    A zone plate (in this context) is a 3 dimensional (horizontal,
    vertical & temporal) frequency sweep which can be a useful test
    pattern in image processing applications. `BBC R&D Report 1978/23
    <http://www.bbc.co.uk/rd/publications/rdreport_1978_23>`_ describes
    some typical uses. A static circular zone plate (see `recipes`_
    below) resembles the `Fresnel zone plates
    <http://en.wikipedia.org/wiki/Zone_plate>`_ used in optics.

    At first sight there are an alarming number of configuration values,
    but you normally only need to set three or four of them. I suggest
    using the :py:mod:`pyctools-editor <pyctools.tools.editor>` tool to
    connect a zone plate generator and Qt display, open the generator's
    configuration dialog, set ``looping`` to ``repeat`` and run the
    network so you can experiment with the settings as you read this
    documentation.

    Each parameter is normalised so a value of ``1.0`` covers the entire
    frequency "gamut". For example, setting ``kx2`` to ``1.0`` will
    sweep the entire horizontal frequency range over the width of the
    picture.

    =======  ========
    name     controls
    =======  ========
    ``k0``   phase at zero frequency
    ``kx``   horizontal frequency at x=0 (left hand side of picture)
    ``ky``   vertical frequency at y=0 (top of picture)
    ``kt``   temporal frequency at t=0 (start of sequence)
    ``kx2``  horizontal frequency with x
    ``kxy``  horizontal frequency with y
    ``kxt``  horizontal frequency with t
    ``kyx``  vertical frequency with x
    ``ky2``  vertical frequency with y
    ``kyt``  vertical frequency with t
    ``ktx``  temporal frequency with x
    ``kty``  temporal frequency with y
    ``kt2``  temporal frequency with t
    =======  ========

    Note that these controls are not all independent. For example,
    ``kxy`` and ``kyx`` produce the same effect on a square image (and a
    subtly different effect on non-square images).

    .. _recipes:

    Recipes

    * static circular (or eliptical for non-square images)::

        kx=0.5, kx2 = 1.0, ky=0.5, ky2=1.0

    * static hyperbolic (entire horizontal gamut)::

        kx=0.5, kxy = 1.0, ky=0.5

    * static hyperbolic (entire vertical gamut)::

        kx=0.5, ky=0.5, kyx = 1.0

    * circular at temporal frequency of 1/4 the frame rate::

        kx=0.5, kx2 = 1.0, ky=0.5, ky2=1.0, kt=0.25

    * all temporal frequencies across width, all vertical frequencies
      across height::

        ky=0.5, ky2=1.0, ktx=1.0

    """

    inputs = []

    def initialise(self):
        self.config['k0'] = ConfigFloat(
            value=0.0, min_value=-1.0, max_value=1.0, decimals=4, wrapping=True)
        self.config['kx'] = ConfigFloat(
            value=0.0, min_value=-1.0, max_value=1.0, decimals=4, wrapping=True)
        self.config['ky'] = ConfigFloat(
            value=0.0, min_value=-1.0, max_value=1.0, decimals=4, wrapping=True)
        self.config['kt'] = ConfigFloat(
            value=0.0, min_value=-1.0, max_value=1.0, decimals=4, wrapping=True)
        self.config['kx2'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=4)
        self.config['kxy'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=4)
        self.config['kxt'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=4)
        self.config['kyx'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=4)
        self.config['ky2'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=4,
            wrapping=True)
        self.config['kyt'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=4)
        self.config['ktx'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=4)
        self.config['kty'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=4)
        self.config['kt2'] = ConfigFloat(
            value=0.0, min_value=-100.0, max_value=100.0, decimals=4)
        self.config['xlen'] = ConfigInt(value=720, min_value=1)
        self.config['ylen'] = ConfigInt(value=576, min_value=1)
        self.config['zlen'] = ConfigInt(value=100, min_value=1)
        self.config['looping'] = ConfigEnum(choices=('off', 'repeat'))
        # store sine wave in a lookup table
        self.phases = 1024
        self.waveform = numpy.ndarray([self.phases], dtype=numpy.float32)
        for i in range(self.phases):
            phase = float(i) / float(self.phases)
            self.waveform[i] = 16.0 + (
                219.0 * (1.0 + math.cos(phase * math.pi * 2.0)) / 2.0)
        self.frame_no = 0

    def process_frame(self):
        self.update_config()
        xlen = self.config['xlen']
        ylen = self.config['ylen']
        zlen = self.config['zlen']
        if self.frame_no >= zlen and self.config['looping'] == 'off':
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
        frame = self.outframe_pool['output'].get()
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
        data = numpy.ndarray([ylen, xlen, 1], dtype=numpy.float32)
        zone_frame(data, self.waveform, self.frame_no % zlen,
                   k0, kx, ky, kt, kx2, kxy, kxt, kyx, ky2, kyt, ktx, kty, kt2)
        # set output frame
        frame.data = data
        frame.type = 'Y'
        frame.frame_no = self.frame_no
        self.frame_no += 1
        self.send('output', frame)
