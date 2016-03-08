#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2016  Pyctools contributors
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

__all__ = ['GammaCorrect']
__docformat__ = 'restructuredtext en'

from collections import OrderedDict
import math

import sys
if 'sphinx' in sys.modules:
    __all__ += ['apply_transfer_function']

import numpy

from pyctools.core.config import ConfigBool, ConfigEnum, ConfigFloat
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float
from .gammacorrectioncore import apply_transfer_function

class GammaCorrect(Transformer):
    """Gamma correction.

    Convert linear intensity values to 'gamma corrected' form suitable
    for display or storage in standard video or image files.

    In ``inverse`` mode gamma corrected data is converted to linear
    intensity.

    The ``'hybrid_log'`` gamma option is an implementation of a proposal
    from `BBC R&D <http://www.bbc.co.uk/rd>`_ for `HDR imaging
    <https://en.wikipedia.org/wiki/High-dynamic-range_imaging>`_. See
    http://www.bbc.co.uk/rd/publications/whitepaper309 for more
    information.

    The ``range`` config item specifies the input and output video
    ranges. It can be either ``'studio'`` (16..235) or ``'computer'``
    (0..255).

    ==============  =====  ====
    Config
    ==============  =====  ====
    ``range``       str    Nominal black and white levels. Can be ``'studio'`` or ``'computer'``.
    ``scale``       float  Adjust nominal white level of input data.
    ``gamma``       str    Choose a gamma curve. Possible values: {}.
    ``knee``        bool   Turn on "knee" (highlight compression).
    ``knee_point``  float  Highlight compression threshold (normalised 0..1 range).
    ``knee_slope``  float  Slope of transfer function above knee threshold.
    ``inverse``     bool
    ==============  =====  ====

    """

    gamma_toe = OrderedDict([
        # name          gamma          toe    threshold  "a"
        ('linear',     (1.0,           1.0,   0.0 ,      0.0)),
        ('bt709',      (0.45,          4.5,   0.018,     0.099)),
        ('srgb',       (1.0 / 2.4,     12.92, 0.0031308, 0.055)),
        ('adobe_rgb',  (256.0 / 563.0, 0.0,   0.0,       0.0)),
        ('hybrid_log', (1.0 / 2.0,     0.0,   0.0,       0.0)),
        ])

    __doc__ = __doc__.format(', '.join(["``'" + x + "'``" for x in gamma_toe]))

    def initialise(self):
        self.config['range'] = ConfigEnum(('studio', 'computer'))
        self.config['scale'] = ConfigFloat(value=1.0, decimals=2)
        self.config['gamma'] = ConfigEnum(list(self.gamma_toe.keys()))
        self.config['inverse'] = ConfigBool()
        self.config['knee'] = ConfigBool()
        self.config['knee_point'] = ConfigFloat(value=0.9, decimals=2)
        self.config['knee_slope'] = ConfigFloat(value=0.25, decimals=2)

    def on_start(self):
        self.update_config()
        self.adjust_params()

    def adjust_params(self):
        gamma, toe, threshold, k_a = self.gamma_toe[self.config['gamma']]
        # threshold for switch from linear to exponential
        if threshold is None:
            # first approximate value, ignoring extra scaling factor a
            threshold = (toe / gamma) ** (1.0 / (gamma - 1.0))
            # refine using Newton-Raphson method
            last_err = 1.0
            while True:
                f_p = (((1.0 - gamma) * (threshold ** gamma)) +
                       ((gamma / toe) *
                        (threshold ** (gamma - 1.0))) - 1.0)
                df_p = (((1.0 - gamma) * gamma *
                         (threshold ** (gamma - 1.0))) +
                        ((gamma / toe) * (gamma - 1.0) *
                         (threshold ** (gamma - 2.0))))
                err = f_p / df_p
                if abs(err) >= last_err:
                    break
                last_err = abs(err)
                threshold -= err
        if k_a is None:
            k_a = (1.0 - gamma) * (threshold ** gamma)
            k_a = k_a / (1.0 - k_a)
        self.in_val = numpy.ndarray(512, dtype=pt_float)
        self.out_val = numpy.ndarray(self.in_val.shape, dtype=pt_float)
        scale = pt_float(self.config['scale'])
        knee = self.config['knee']
        knee_point = self.config['knee_point']
        knee_slope = self.config['knee_slope']
        knee_idx = 0
        ka = 0.17883277
        kb = 0.28466892
        kc = 0.55991073
        for i in range(self.in_val.shape[0]):
            v = ((float(i) / float(self.in_val.shape[0])) * 2.0) - 0.5
            self.in_val[i] = v
            if knee and v <= knee_point:
                knee_idx = i
            if knee and v > knee_point:
                v = self.out_val[knee_idx] + (
                    knee_slope * (v - self.in_val[knee_idx]))
            elif self.config['gamma'] == 'hybrid_log':
                v *= 6.0
                if v <= 0.0:
                    v = 0.0
                elif v <= 1.0:
                    v = 0.5 * math.sqrt(v)
                else:
                    v = (ka * math.log(v - kb)) + kc
            elif gamma != 1.0:
                # conventional gamma + linear toe
                if v <= threshold:
                    v *= toe
                else:
                    v = v ** gamma
                    v = ((1.0 + k_a) * v) - k_a
            self.out_val[i] = v
        # scale values to normal video range
        self.in_val *= pt_float(scale)
        self.out_val *= pt_float(scale)
        if self.config['range'] == 'studio':
            self.in_val *= pt_float(219.0)
            self.out_val *= pt_float(219.0)
            self.in_val += pt_float(16.0)
            self.out_val += pt_float(16.0)
        else:
            self.in_val *= pt_float(255.0)
            self.out_val *= pt_float(255.0)

    def transform(self, in_frame, out_frame):
        if self.update_config():
            self.adjust_params()
        inverse = self.config['inverse']
        data = in_frame.as_numpy(dtype=pt_float, copy=True)
        if inverse:
            apply_transfer_function(data, self.out_val, self.in_val)
        else:
            apply_transfer_function(data, self.in_val, self.out_val)
        out_frame.data = data
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = {}GammaCorrect(data, {})\n'.format(
            ('', 'Inverse ')[inverse], self.config['gamma'])
        out_frame.metadata.set('audit', audit)
        return True
