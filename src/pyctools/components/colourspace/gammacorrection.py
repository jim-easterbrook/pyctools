#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2015-16  Pyctools contributors
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
            'srgb'      : (1.0 / 2.4, 12.92),
            'adobe_rgb' : (0.4547069271758437, 0.0),
            }[self.config['gamma']]
        # threshold for switch from linear to exponential
        if gamma == 1.0 or toe <= 0.0:
            threshold = 0.0
            a = 0.0
        else:
            # first approximate value, ignoring extra scaling factor a
            threshold = (toe / gamma) ** (1.0 / (gamma - 1.0))
            # refine using Newton-Raphson method
            last_err = 1.0
            while True:
                f_p = (((1.0 - gamma) * (threshold ** gamma)) +
                       ((gamma / toe) * (threshold ** (gamma - 1.0))) - 1.0)
                df_p = (((1.0 - gamma) * gamma * (threshold ** (gamma - 1.0))) +
                        ((gamma / toe) * (gamma - 1.0) *
                         (threshold ** (gamma - 2.0))))
                err = f_p / df_p
                if abs(err) >= last_err:
                    break
                last_err = abs(err)
                threshold -= err
            a = (1.0 - gamma) * (threshold ** gamma)
            a = a / (1.0 - a)
        # get data
        data = in_frame.as_numpy()
        if gamma == 1.0:
            # nothing to do
            out_frame.data = data
        else:
            # convert range to 0..1
            if self.config['range'] == 'studio':
                data = (data - pt_float(16.0)) / pt_float(219.0)
            else:
                data = data / pt_float(255.0)
            # apply gamma function
            exp_data = numpy.fmax(data, pt_float(0.0)) ** pt_float(gamma)
            if a != 0.0:
                exp_data = (pt_float(1.0 + a) * exp_data) - pt_float(a)
            if threshold <= 0.0:
                data = exp_data
            else:
                toe_data = data * pt_float(toe)
                data = numpy.where(
                    data > pt_float(threshold), exp_data, toe_data)
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
