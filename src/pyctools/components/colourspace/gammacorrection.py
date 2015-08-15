#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2015  Pyctools contributors
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

"""Gamma correction.

Convert linear intensity values to 'gamma corrected' form suitable for
display or storage in standard video or image files.

The ``range`` config item specifies the input video range. It can be
either ``'studio'`` (16..235) or ``'computer'`` (0..255).

===================  =====  ====
Config
===================  =====  ====
``range``            str    Nominal black and white levels. Can be ``'studio'`` or ``'computer'``.
``gamma``            str    Choose a gamma curve. Can be ``'linear'``, ``'bt709'``, ``'srgb'`` or ``'adobe_rgb'``.
===================  =====  ====

"""

__all__ = ['GammaCorrect']
__docformat__ = 'restructuredtext en'

import math

import numpy

from pyctools.core.config import ConfigEnum
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float

class GammaCorrect(Transformer):
    def initialise(self):
        self.config['range'] = ConfigEnum(('studio', 'computer'))
        self.config['gamma'] = ConfigEnum((
            'linear', 'bt709', 'srgb', 'adobe_rgb'))

    def transform(self, in_frame, out_frame):
        self.update_config()
        gamma, toe = {
            'linear'    : (1.0, 1.0),
            'bt709'     : (0.45004500450045004, 4.5),
            'srgb'      : (0.4166666666666667, 12.92),
            'adobe_rgb' : (0.4547069271758437, 0.0),
            }[self.config['gamma']]
        # threshold for switch from linear to exponential
        if gamma == 1.0:
            threshold = 1.0
        elif toe > 0.0:
            threshold = math.exp(math.log(toe) / (gamma - 1.0))
        else:
            threshold = 0.0
            toe = 0.0
        # get data
        data = in_frame.as_numpy()
        # convert range to 0..1
        if self.config['range'] == 'studio':
            data = (data - pt_float(16.0)) / pt_float(219.0)
        else:
            data = data / pt_float(255.0)
        # apply gamma function
        exp_data = numpy.fmax(data, pt_float(0.0)) ** pt_float(gamma)
        toe_data = data * pt_float(toe)
        data = numpy.where(data > pt_float(threshold), exp_data, toe_data)
        # convert back to input range
        if self.config['range'] == 'studio':
            out_frame.data = (data * pt_float(219.0)) + pt_float(16.0)
        else:
            out_frame.data = data * pt_float(255.0)
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = GammaCorrect(data, {}, {})\n'.format(gamma, toe)
        out_frame.metadata.set('audit', audit)
        return True
