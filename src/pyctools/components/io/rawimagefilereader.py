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

"""Read 'raw' still image file (CR2, etc.).

===================  =====  ====
Config
===================  =====  ====
``path``             str    Path name of file to be read.
``16bit``            str    Get greater precision than normal 8-bit range. Can be ``'off'`` or ``'on'``.
``brightness``       float  Set the gain.
``gamma``            str    Choose a gamma curve. Can be ``'linear'``, ``'bt709'``, ``'srgb'`` or ``'adobe_rgb'``.
``interpolation``    str    Choose a demosaicing method. Can be ``'linear'``, ``'vng'``, ``'ppg'``, ``'ahd'`` or ``'dcb'``.
``noise_threshold``  float  Set a denoising threshold. Typically 100 to 1000.
===================  =====  ====

"""

from __future__ import print_function

__all__ = ['RawImageFileReader']
__docformat__ = 'restructuredtext en'

import time

import numpy
from rawkit.raw import Raw
from rawkit.options import gamma_curves, interpolation, WhiteBalance

from pyctools.core.config import ConfigPath, ConfigEnum, ConfigFloat
from pyctools.core.base import Component
from pyctools.core.frame import Frame
from pyctools.core.types import pt_float

class RawImageFileReader(Component):
    inputs = []
    with_outframe_pool = False

    def initialise(self):
        self.config['path'] = ConfigPath()
        self.config['16bit'] = ConfigEnum(('off', 'on'))
        self.config['brightness'] = ConfigFloat(value=1.0, decimals=2)
        self.config['gamma'] = ConfigEnum((
            'linear', 'bt709', 'srgb', 'adobe_rgb'))
        self.config['interpolation'] = ConfigEnum((
            'linear', 'vng', 'ppg', 'ahd', 'dcb'))
        self.config['noise_threshold'] = ConfigFloat(value=0, decimals=0)

    def on_start(self):
        # read file
        self.update_config()
        path = self.config['path']
        bit16 = self.config['16bit'] != 'off'
        with Raw(filename=path) as raw:
            raw.options.auto_brightness = False
            raw.options.brightness = self.config['brightness']
            raw.options.gamma = {
                'linear'    : gamma_curves.linear,
                'bt709'     : gamma_curves.bt709,
                'srgb'      : gamma_curves.srgb,
                'adobe_rgb' : gamma_curves.adobe_rgb,
                }[self.config['gamma']]
            raw.options.interpolation = {
                'linear' : interpolation.linear,
                'vng'    : interpolation.vng,
                'ppg'    : interpolation.ppg,
                'ahd'    : interpolation.ahd,
                'dcb'    : interpolation.dcb,
                }[self.config['interpolation']]
            raw.options.bps = (8, 16)[bit16]
            noise_threshold = self.config['noise_threshold']
            if noise_threshold != 0:
                raw.options.noise_threshold = noise_threshold
            raw.options.white_balance = WhiteBalance(camera=True, auto=False)
            data = raw.to_buffer()
            if bit16:
                image = numpy.frombuffer(data, dtype=numpy.uint16)
                image = image.astype(pt_float) / pt_float(256.0)
            else:
                image = numpy.frombuffer(data, dtype=numpy.uint8)
            image = image.reshape((raw.metadata.height, raw.metadata.width, 3))
        out_frame = Frame()
        # send output frame
        out_frame.data = image
        out_frame.type = 'RGB'
        out_frame.frame_no = 0
        out_frame.metadata.from_file(path)
        audit = out_frame.metadata.get('audit')
        audit += 'data = %s\n' % path
        out_frame.metadata.set('audit', audit)
        self.send('output', out_frame)
        # shut down pipeline
        self.stop()
