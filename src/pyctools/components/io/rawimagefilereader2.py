#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2019  Pyctools contributors
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

__all__ = ['RawImageFileReader2']
__docformat__ = 'restructuredtext en'

import os

import numpy
import rawpy

from pyctools.core.config import (
    ConfigBool, ConfigEnum, ConfigFloat, ConfigInt, ConfigPath, ConfigStr)
from pyctools.core.base import Component
from pyctools.core.frame import Frame, Metadata
from pyctools.core.types import pt_float


class RawImageFileReader2(Component):
    """Read 'raw' still image file (CR2, NEF, etc.).

    This component uses the rawpy_ Python package. See
    :py:class:`~.rawimagefilereader.RawImageFileReader` for a component
    that uses rawkit.

    Note that the file is always read in 16-bit linear mode. You will
    need to convert the image to "gamma corrected" mode before
    displaying it or saving it to JPEG or similar. See
    :py:mod:`~pyctools.components.colourspace.gammacorrection` for some
    useful components.

    Some options add significantly to the processing time, particularly
    ``fbdd_noise_reduction`` and some of the ``demosaic_algorithm``
    options.

    ========================  =====  ====
    Config
    ========================  =====  ====
    ``path``                  str    Path name of file to be read.
    ``demosaic_algorithm``    str    Set demosaicing method. Possible values: {}.
    ``four_color_rgb``        bool   Use separate interpolation for 2 green channels.
    ``dcb_iterations``        int    Number of passes of DCB interpolation.
    ``dcb_enhance``           bool   Enhance colours of DCB interpolation.
    ``fbdd_noise_reduction``  str    Enable FBDD noise reduction before demosaicing. Possible values: {}.
    ``noise_thr``             float  Set denoising threshold. Typically 100 to 1000.
    ``median_filter_passes``  int    Number of median filter passes after demosaicing.
    ``use_camera_wb``         bool   Use camera defined white balance.
    ``use_auto_wb``           bool   Automatic white balance.
    ``user_wb``               str    4 comma separated floats that set the gain of each channel.
    ``output_color``          str    Set colour space. Possible values: {}.
    ``bright``                float  Brightness / white level scaling.
    ``highlight_mode``        str    Set highlight mode. Possible values: {}.
    ``exp_shift``             float  Exposure shift. Darken if < 1.0, lighten if > 1.0.
    ``red_scale``             float  Chromatic aberration correction red scale factor.
    ``blue_scale``            float  Chromatic aberration correction blue scale factor.
    ``crop``                  bool   Auto crop image to dimensions in metadata.
    ========================  =====  ====

    .. _rawpy: https://letmaik.github.io/rawpy/

    """

    __doc__ = __doc__.format(
        ', '.join(["``'" + x.name + "'``"
                   for x in rawpy.DemosaicAlgorithm if x.isSupported]),
        ', '.join(["``'" + x.name + "'``"
                   for x in rawpy.FBDDNoiseReductionMode]),
        ', '.join(["``'" + x.name + "'``" for x in rawpy.ColorSpace]),
        ', '.join(["``'" + x.name + "'``" for x in rawpy.HighlightMode]))

    inputs = []
    with_outframe_pool = False

    def initialise(self):
        self.config['path'] = ConfigPath()
        self.config['demosaic_algorithm'] = ConfigEnum(
            choices=[x.name for x in rawpy.DemosaicAlgorithm if x.isSupported],
            value='AHD')
        self.config['four_color_rgb'] = ConfigBool()
        self.config['dcb_iterations'] = ConfigInt(min_value=0)
        self.config['dcb_enhance'] = ConfigBool()
        self.config['fbdd_noise_reduction'] = ConfigEnum(
            choices=[x.name for x in rawpy.FBDDNoiseReductionMode])
        self.config['noise_thr'] = ConfigFloat(value=0, decimals=0)
        self.config['median_filter_passes'] = ConfigInt(min_value=0)
        self.config['use_camera_wb'] = ConfigBool(value=True)
        self.config['use_auto_wb'] = ConfigBool(value=False)
        self.config['user_wb'] = ConfigStr()
        self.config['output_color'] = ConfigEnum(
            choices=[x.name for x in rawpy.ColorSpace], value='sRGB')
        self.config['bright'] = ConfigFloat(value=1.0, decimals=2)
        self.config['highlight_mode'] = ConfigEnum(
            choices=[x.name for x in rawpy.HighlightMode], value='Blend')
        self.config['exp_shift'] = ConfigFloat(value=1.0, decimals=2,
                                               min_value=0.25, max_value=8.0)
        self.config['red_scale'] = ConfigFloat(value=1.0, decimals=5)
        self.config['blue_scale'] = ConfigFloat(value=1.0, decimals=5)
        self.config['crop'] = ConfigBool(value=True)

    def on_start(self):
        # read file
        self.update_config()
        path = self.config['path']
        params = {
            'demosaic_algorithm': rawpy.DemosaicAlgorithm[
                self.config['demosaic_algorithm']],
            'four_color_rgb': self.config['four_color_rgb'],
            'dcb_iterations': self.config['dcb_iterations'],
            'dcb_enhance': self.config['dcb_enhance'],
            'fbdd_noise_reduction': rawpy.FBDDNoiseReductionMode[
                self.config['fbdd_noise_reduction']],
            'median_filter_passes': self.config['median_filter_passes'],
            'use_camera_wb': self.config['use_camera_wb'],
            'use_auto_wb': self.config['use_auto_wb'],
            'output_color': rawpy.ColorSpace[self.config['output_color']],
            'output_bps': 16,
            'user_flip': 0,
            'no_auto_bright': True,
            'bright': self.config['bright'],
            'highlight_mode': rawpy.HighlightMode[
                self.config['highlight_mode']],
            'exp_shift': self.config['exp_shift'],
            'gamma': (1.0, 1.0),
            'chromatic_aberration': (self.config['red_scale'],
                                     self.config['blue_scale']),
            }
        if self.config['noise_thr'] != 0:
            params['noise_thr'] = self.config['noise_thr']
        if self.config['user_wb']:
            params['user_wb'] = eval('(' + self.config['user_wb'] + ')')
        with rawpy.imread(path) as raw:
            image = raw.postprocess(**params)
            if self.config['crop']:
                w, h = Metadata().from_file(path).image_size()
                x = (image.shape[1] - w) // 2
                y = (image.shape[0] - h) // 2
                image = image[y:y+h, x:x+w, :]
            image = image.astype(pt_float) / pt_float(256.0)
        out_frame = Frame()
        # send output frame
        out_frame.data = image
        out_frame.type = 'RGB'
        out_frame.frame_no = 0
        out_frame.metadata.from_file(path)
        audit = out_frame.metadata.get('audit')
        audit += 'data = RawImageFileReader2({})\n'.format(
            os.path.basename(path))
        audit += self.config.audit_string()
        out_frame.metadata.set('audit', audit)
        self.send('output', out_frame)
        # shut down pipeline
        self.stop()
