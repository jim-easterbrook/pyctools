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

__all__ = ['GammaCorrect', 'PiecewiseGammaCorrect']
__docformat__ = 'restructuredtext en'

from collections import OrderedDict
import math

import sys
if 'sphinx' in sys.modules:
    __all__ += ['apply_transfer_function']

import numpy

from pyctools.core.config import ConfigBool, ConfigEnum, ConfigFloat, ConfigStr
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

    The ``'S-Log'`` option is taken from a Sony document
    https://pro.sony.com/bbsccms/assets/files/mkt/cinema/solutions/slog_manual.pdf

    The ``range`` config item specifies the gamma corrected black to
    white range. It can be either ``'studio'`` (16..235) or
    ``'computer'`` (0..255). The linear intensity black and white values
    are set by the ``black`` and ``white`` config items.

    The ``function`` output emits the transfer function data whenever it
    changes. It can be connected to the
    :py:class:`~pyctools.components.io.plotdata.PlotData` component.

    ==============  =====  ====
    Config
    ==============  =====  ====
    ``range``       str    Nominal gamma corrected black and white levels. Can be ``'studio'`` or ``'computer'``.
    ``black``       float  "Linear intensity" black level.
    ``white``       float  "Linear intensity" white level.
    ``gamma``       str    Choose a gamma curve. Possible values: {}.
    ``knee``        bool   Turn on "knee" (highlight compression).
    ``knee_point``  float  Highlight compression threshold (normalised 0..1 range).
    ``knee_slope``  float  Slope of transfer function above knee threshold.
    ``inverse``     bool
    ==============  =====  ====

    """
    outputs = ['output', 'function']
    gamma_toe = OrderedDict([
        # name          gamma          toe    threshold  "a"
        ('linear',     (1.0,           1.0,   0.0 ,      0.0)),
        ('bt709',      (0.45,          4.5,   0.018,     0.099)),
        ('srgb',       (1.0 / 2.4,     12.92, 0.0031308, 0.055)),
        ('adobe_rgb',  (256.0 / 563.0, 0.0,   0.0,       0.0)),
        ('hybrid_log', (1.0 / 2.0,     0.0,   0.0,       0.0)),
        ('S-Log',      (None,          0.0,   0.0,       0.0)),
        ])
    __doc__ = __doc__.format(', '.join(["``'" + x + "'``" for x in gamma_toe]))

    def initialise(self):
        self.config['range'] = ConfigEnum(('studio', 'computer'))
        self.config['gamma'] = ConfigEnum(list(self.gamma_toe.keys()))
        self.config['black'] = ConfigFloat(value=0.0, decimals=2)
        self.config['white'] = ConfigFloat(value=255.0, decimals=2)
        self.config['inverse'] = ConfigBool()
        self.config['knee'] = ConfigBool()
        self.config['knee_point'] = ConfigFloat(value=0.9, decimals=2)
        self.config['knee_slope'] = ConfigFloat(value=0.25, decimals=2)
        self.initialised = False

    def adjust_params(self):
        self.initialised = True
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
        # make list of in and out values
        in_val = []
        out_val = []
        knee = self.config['knee']
        knee_point = self.config['knee_point']
        knee_slope = self.config['knee_slope']
        ka = 0.17883277
        kb = 0.28466892
        kc = 0.55991073
        # toe section just needs two end points
        v_in = -0.1
        v_out = v_in * toe
        in_val.append(v_in)
        out_val.append(v_out)
        v_in = threshold
        v_out = v_in * toe
        in_val.append(v_in)
        out_val.append(v_out)
        # complicated section needs many points
        while v_in < 10.0:
            v_in += 0.01
            if knee:
                v_in = min(v_in, knee_point)
            if self.config['gamma'] == 'hybrid_log':
                if v_in <= 1.0:
                    v_out = 0.5 * math.sqrt(v_in)
                else:
                    v_out = (ka * math.log(v_in - kb)) + kc
                v_out *= 2.0
            elif self.config['gamma'] == 'S-Log':
                v_out = (0.432699 * math.log10(v_in + 0.037584)) + 0.616596 + 0.03
            else:
                v_out = v_in ** gamma
                v_out = ((1.0 + k_a) * v_out) - k_a
            if abs(v_out - out_val[-1]) >= 0.005:
                in_val.append(v_in)
                out_val.append(v_out)
            if knee and v_in >= knee_point:
                break
        # knee section just needs another endpoint
        if knee:
            v_in = max(10.0, in_val[-1] + 0.1)
            v_out = out_val[-1] + (knee_slope * (v_in - in_val[-1]))
            in_val.append(v_in)
            out_val.append(v_out)
        self.in_val = numpy.array(in_val, dtype=pt_float)
        self.out_val = numpy.array(out_val, dtype=pt_float)
        # scale "linear" values
        black = self.config['black']
        white = self.config['white']
        self.in_val *= pt_float(white - black)
        self.in_val += pt_float(black)
        # scale gamma corrected values to normal video range
        if self.config['range'] == 'studio':
            self.out_val *= pt_float(219.0)
            self.out_val += pt_float(16.0)
        else:
            self.out_val *= pt_float(255.0)
        # send to function output
        func_frame = self.outframe_pool['function'].get()
        func_frame.data = numpy.stack((self.in_val, self.out_val))
        func_frame.type = 'func'
        audit = func_frame.metadata.get('audit')
        audit += 'data = GammaFunction({})\n'.format(self.config['gamma'])
        func_frame.metadata.set('audit', audit)
        self.send('function', func_frame)

    def transform(self, in_frame, out_frame):
        if self.update_config() or not self.initialised:
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


class PiecewiseGammaCorrect(Transformer):
    """Gamma correction with a piecewise linear transform.

    The transform is specified as a series of input values and
    corresponding output values. Linear interpolation is used to convert
    data that lies between ``in_vals`` values, and extrapolation is used
    for data outside the range of ``in_vals``.

    The ``function`` output emits the transfer function data whenever it
    changes. It can be connected to the
    :py:class:`~pyctools.components.io.plotdata.PlotData` component.

    ==============  =====  ====
    Config
    ==============  =====  ====
    ``in_vals``     str    List of input values, in increasing order.
    ``out_vals``    str    List of corresponding output values.
    ``inverse``     bool
    ==============  =====  ====

    """
    outputs = ['output', 'function']

    def initialise(self):
        self.config['in_vals'] = ConfigStr(value='0.0, 255.0')
        self.config['out_vals'] = ConfigStr(value='0.0, 255.0')
        self.config['inverse'] = ConfigBool()
        self.initialised = False

    def adjust_params(self):
        self.initialised = True
        in_vals = eval(self.config['in_vals'])
        out_vals = eval(self.config['out_vals'])
        self.in_vals = numpy.array(in_vals, dtype=pt_float)
        self.out_vals = numpy.array(out_vals, dtype=pt_float)
        func_frame = self.outframe_pool['function'].get()
        func_frame.data = numpy.stack((self.in_vals, self.out_vals))
        func_frame.type = 'func'
        audit = func_frame.metadata.get('audit')
        audit += 'data = PiecewiseGammaFunction()\n'
        audit += '    in_vals: {}\n'.format(self.config['in_vals'])
        audit += '    out_vals: {}\n'.format(self.config['out_vals'])
        func_frame.metadata.set('audit', audit)
        self.send('function', func_frame)

    def transform(self, in_frame, out_frame):
        if self.update_config() or not self.initialised:
            self.adjust_params()
        inverse = self.config['inverse']
        data = in_frame.as_numpy(dtype=pt_float, copy=True)
        if inverse:
            apply_transfer_function(data, self.out_vals, self.in_vals)
        else:
            apply_transfer_function(data, self.in_vals, self.out_vals)
        out_frame.data = data
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = {}PiecewiseGammaCorrect(data)\n'.format(('', 'Inverse ')[inverse])
        audit += '    in_vals: {}\n'.format(self.config['in_vals'])
        audit += '    out_vals: {}\n'.format(self.config['out_vals'])
        out_frame.metadata.set('audit', audit)
        return True
