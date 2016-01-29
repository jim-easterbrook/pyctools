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

"""Gamma correction.

Convert linear intensity values to 'gamma corrected' form suitable for
display or storage in standard video or image files.

In ``inverse`` mode gamma corrected data is converted to linear
intensity.

The ``'hybrid_log'`` gamma option is an implementation of a proposal
from BBC R&D for HDR imaging. See
http://www.bbc.co.uk/rd/publications/whitepaper309 for more information.

The ``range`` config item specifies the input and output video ranges.
It can be either ``'studio'`` (16..235) or ``'computer'`` (0..255).

===========  ===  ====
Config
===========  ===  ====
``range``    str  Nominal black and white levels. Can be ``'studio'`` or ``'computer'``.
``gamma``    str  Choose a gamma curve. Possible values: {}.
``inverse``  str  Can be set to ``off`` or ``on``.
===========  ===  ====

"""

__all__ = ['GammaCorrect']
__docformat__ = 'restructuredtext en'

from collections import OrderedDict

import numpy

from pyctools.core.config import ConfigEnum
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float
from .gammacorrectioncore import gamma_frame, hybrid_gamma_frame, inverse_gamma_frame

gamma_toe = OrderedDict([
    ('linear',     (1.0, 1.0)),
    ('bt709',      (0.45, 4.5)),
    ('srgb',       (1.0 / 2.4, 12.92)),
    ('adobe_rgb',  (256.0 / 563.0, 0.0)),
    ('hybrid_log', (1.0 / 2.0, 0.0)),
    ])

__doc__ = __doc__.format(', '.join(["``'" + x + "'``" for x in gamma_toe]))

class GammaCorrect(Transformer):
    def initialise(self):
        self.config['range'] = ConfigEnum(('studio', 'computer'))
        self.config['gamma'] = ConfigEnum(list(gamma_toe.keys()))
        self.config['inverse'] = ConfigEnum(('off', 'on'))

    def on_start(self):
        self.update_config()
        self.adjust_params()

    def adjust_params(self):
        self.gamma, self.toe = gamma_toe[self.config['gamma']]
        self.inverse = self.config['inverse'] == 'on'
        # threshold for switch from linear to exponential
        if self.gamma == 1.0 or self.toe <= 0.0:
            self.threshold = 0.0
            self.a = 0.0
        else:
            # first approximate value, ignoring extra scaling factor a
            self.threshold = (self.toe / self.gamma) ** (1.0 / (self.gamma - 1.0))
            # refine using Newton-Raphson method
            last_err = 1.0
            while True:
                f_p = (((1.0 - self.gamma) * (self.threshold ** self.gamma)) +
                       ((self.gamma / self.toe) *
                        (self.threshold ** (self.gamma - 1.0))) - 1.0)
                df_p = (((1.0 - self.gamma) * self.gamma *
                         (self.threshold ** (self.gamma - 1.0))) +
                        ((self.gamma / self.toe) * (self.gamma - 1.0) *
                         (self.threshold ** (self.gamma - 2.0))))
                err = f_p / df_p
                if abs(err) >= last_err:
                    break
                last_err = abs(err)
                self.threshold -= err
            self.a = (1.0 - self.gamma) * (self.threshold ** self.gamma)
            self.a = self.a / (1.0 - self.a)

    def transform(self, in_frame, out_frame):
        if self.update_config():
            self.adjust_params()
        # get data
        if self.gamma != 1.0:
            data = in_frame.as_numpy(dtype=pt_float, copy=True)
            # convert range to 0..1 (and copy data)
            if self.config['range'] == 'studio':
                data -= pt_float(16.0)
                data /= pt_float(219.0)
            else:
                data /= pt_float(255.0)
            # apply gamma function
            if self.inverse:
                inverse_gamma_frame(
                    data, self.gamma, self.toe, self.threshold, self.a)
            elif self.config['gamma'] == 'hybrid_log':
                hybrid_gamma_frame(data)
            else:
                gamma_frame(
                    data, self.gamma, self.toe, self.threshold, self.a)
            # convert back to input range
            if self.config['range'] == 'studio':
                data *= pt_float(219.0)
                data += pt_float(16.0)
            else:
                data *= pt_float(255.0)
            out_frame.data = data
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = {}GammaCorrect(data, {}, {})\n'.format(
            ('', 'Inverse ')[self.inverse], self.gamma, self.toe)
        out_frame.metadata.set('audit', audit)
        return True
