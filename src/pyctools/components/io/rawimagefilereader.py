#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-19  Pyctools contributors
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

from __future__ import print_function

__all__ = ['RawImageFileReader']
__docformat__ = 'restructuredtext en'

import os

import numpy
from rawkit.raw import Raw
from rawkit.options import (
    colorspaces, gamma_curves, highlight_modes, interpolation, WhiteBalance)

from pyctools.core.config import (
    ConfigBool, ConfigEnum, ConfigFloat, ConfigPath, ConfigStr)
from pyctools.core.base import Component
from pyctools.core.frame import Frame, Metadata
from pyctools.core.types import pt_float


class RawImageFileReader(Component):
    """Read 'raw' still image file (CR2, NEF, etc.).

    This component uses the rawkit_ Python package. See
    :py:class:`~.rawimagefilereader2.RawImageFileReader2` for a component
    that uses rawpy.

    See the `rawkit documentation
    <https://rawkit.readthedocs.io/en/latest/api/rawkit.html>`_ for
    more detail on the configuration options.

    ======================  =====  ====
    Config
    ======================  =====  ====
    ``path``                str    Path name of file to be read.
    ``16bit``               bool   Get greater precision than normal 8-bit range.
    ``brightness``          float  Set the gain.
    ``highlight_mode``      str    Set highlight mode. Possible values: {}.
    ``gamma``               str    Set gamma curve. Possible values: {}.
    ``colourspace``         str    Set colour space. Possible values: {}.
    ``interpolation``       str    Set demosaicing method. Possible values: {}.
    ``noise_threshold``     float  Set denoising threshold. Typically 100 to 1000.
    ``wb_auto``             bool   Automatic white balance.
    ``wb_camera``           bool   Use camera defined white balance.
    ``wb_greybox``          str    4 comma separated integers that define a grey area of the image.
    ``wb_rgbg``             str    4 comma separated floats that set the gain of each channel.
    ``red_scale``           float  Chromatic aberration correction red scale factor.
    ``blue_scale``          float  Chromatic aberration correction blue scale factor.
    ``crop``                bool   Auto crop image to dimensions in metadata.
    ``use_camera_profile``  bool   Use embedded camera profile, if present.
    ======================  =====  ====

    .. _rawkit: https://rawkit.readthedocs.io/

    """

    __doc__ = __doc__.format(
        ', '.join(["``'" + x + "'``" for x in highlight_modes._fields]),
        ', '.join(["``'" + x + "'``" for x in gamma_curves._fields]),
        ', '.join(["``'" + x + "'``" for x in colorspaces._fields]),
        ', '.join(["``'" + x + "'``" for x in interpolation._fields]))

    inputs = []
    with_outframe_pool = False

    def initialise(self):
        self.config['path'] = ConfigPath()
        self.config['16bit'] = ConfigBool(value=True)
        self.config['brightness'] = ConfigFloat(value=1.0, decimals=2)
        self.config['highlight_mode'] = ConfigEnum(
            choices=highlight_modes._fields)
        self.config['gamma'] = ConfigEnum(choices=gamma_curves._fields)
        self.config['colourspace'] = ConfigEnum(
            choices=colorspaces._fields, value='srgb')
        self.config['interpolation'] = ConfigEnum(
            choices=interpolation._fields, value='ahd')
        self.config['noise_threshold'] = ConfigFloat(value=0, decimals=0)
        self.config['wb_auto'] = ConfigBool(value=False)
        self.config['wb_camera'] = ConfigBool(value=True)
        self.config['wb_greybox'] = ConfigStr()
        self.config['wb_rgbg'] = ConfigStr()
        self.config['red_scale'] = ConfigFloat(value=1.0, decimals=5)
        self.config['blue_scale'] = ConfigFloat(value=1.0, decimals=5)
        self.config['crop'] = ConfigBool(value=True)
        self.config['use_camera_profile'] = ConfigBool()

    def on_start(self):
        # read file
        self.update_config()
        path = self.config['path']
        with Raw(filename=path) as raw:
            raw.options.auto_brightness = False
            raw.options.rotation = 0
            raw.options.use_camera_profile = self.config['use_camera_profile']
            raw.options.brightness = self.config['brightness']
            raw.options.highlight_mode = getattr(
                highlight_modes, self.config['highlight_mode'])
            raw.options.chromatic_aberration = (
                self.config['red_scale'], self.config['blue_scale'])
            if self.config['crop']:
                w, h = Metadata().from_file(path).image_size()
                x = (raw.metadata.width - w) // 2
                y = (raw.metadata.height - h) // 2
                raw.options.cropbox = x, y, w, h
            raw.options.gamma = getattr(gamma_curves, self.config['gamma'])
            raw.options.colorspace = getattr(
                colorspaces, self.config['colourspace'])
            raw.options.interpolation = getattr(
                interpolation, self.config['interpolation'])
            raw.options.bps = (8, 16)[self.config['16bit']]
            noise_threshold = self.config['noise_threshold']
            if noise_threshold != 0:
                raw.options.noise_threshold = noise_threshold
            wb = {
                'auto'   : self.config['wb_auto'],
                'camera' : self.config['wb_camera'],
                }
            if self.config['wb_greybox']:
                wb['greybox'] = eval('(' + self.config['wb_greybox'] + ')')
            if self.config['wb_rgbg']:
                wb['rgbg'] = eval('(' + self.config['wb_rgbg'] + ')')
            raw.options.white_balance = WhiteBalance(**wb)
            data = raw.to_buffer()
            if self.config['16bit']:
                image = numpy.frombuffer(data, dtype=numpy.uint16)
                clip_count = numpy.count_nonzero(
                    numpy.greater_equal(image, (2 ** 16) - 1))
                image = image.astype(pt_float) / pt_float(256.0)
            else:
                image = numpy.frombuffer(data, dtype=numpy.uint8)
                clip_count = numpy.count_nonzero(
                    numpy.greater_equal(image, (2 ** 8) - 1))
            if clip_count > 0:
                print(os.path.basename(path), 'clipped pixels:', clip_count)
            image = image.reshape((raw.metadata.height, raw.metadata.width, 3))
        out_frame = Frame()
        # send output frame
        out_frame.data = image
        out_frame.type = 'RGB'
        out_frame.frame_no = 0
        out_frame.metadata.from_file(path)
        audit = out_frame.metadata.get('audit')
        audit += 'data = RawImageFileReader({})\n'.format(
            os.path.basename(path))
        audit += self.config.audit_string()
        out_frame.metadata.set('audit', audit)
        self.send('output', out_frame)
        # shut down pipeline
        self.stop()
