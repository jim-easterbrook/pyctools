#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2016-19  Pyctools contributors
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
try:
    from scipy import interpolate
except ImportError:
    interpolate = None

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

    ``'Canon-Log'`` is taken from a white paper on the EOS C300 camera:
    http://learn.usa.canon.com/app/pdfs/white_papers/White_Paper_Clog_optoelectronic.pdf

    The gamma options have all been normalised so that linear intensity
    ``black`` level input produces a gamma corrected output of 0 and
    linear intensity ``white`` level input produces an output of 255.
    The linear intensity black and white values are set by the ``black``
    and ``white`` config items. You can use an
    :py:class:`~pyctools.components.arithmetic.Arithmetic` or
    :py:class:`~pyctools.components.colourspace.levels.ComputerToStudio`
    component to scale the output if required.

    The ``scale`` option adjusts the input and output ranges without
    changing the mapping from input white to output 255. With some
    functions this acts as a highlight compression adjustment.

    The ``function`` output emits the transfer function data whenever it
    changes. It can be connected to a
    :py:class:`~pyctools.components.io.plotdata.PlotData` component.

    ==============  =====  ====
    Config
    ==============  =====  ====
    ``black``       float  "Linear intensity" black level.
    ``white``       float  "Linear intensity" white level.
    ``scale``       float  Adjust the range of some functions.
    ``gamma``       str    Choose a gamma curve. Possible values: {}.
    ``knee``        bool   Turn on "knee" (highlight compression).
    ``knee_point``  float  Highlight compression threshold (normalised 0..1 range).
    ``knee_slope``  float  Slope of transfer function above knee threshold.
    ``inverse``     bool
    ==============  =====  ====

    """
    outputs = ['output', 'function']    #:
    gamma_toe = OrderedDict([
        # name          gamma          toe    threshold  "a"
        ('linear',     (1.0,           1.0,   0.0,       0.0)),
        ('bt709',      (0.45,          4.5,   0.018,     0.099)),
        ('srgb',       (1.0 / 2.4,     12.92, 0.0031308, 0.055)),
        ('adobe_rgb',  (256.0 / 563.0, None,  0.0,       0.0)),
        ('hybrid_log', (None,          None,  0.0,       0.0)),
        ('S-Log',      (None,          None, -0.037584,  0.0)),
        ('Canon-Log',  (None,          None, -0.0452664, 0.0)),
        ])
    __doc__ = __doc__.format(', '.join(["``'" + x + "'``" for x in gamma_toe]))

    def initialise(self):
        self.config['gamma'] = ConfigEnum(choices=(self.gamma_toe.keys()))
        self.config['black'] = ConfigFloat(value=0.0, decimals=2)
        self.config['white'] = ConfigFloat(value=255.0, decimals=2)
        self.config['scale'] = ConfigFloat(value=1.0, decimals=2)
        self.config['inverse'] = ConfigBool()
        self.config['knee'] = ConfigBool()
        self.config['knee_point'] = ConfigFloat(value=0.9, decimals=3)
        self.config['knee_slope'] = ConfigFloat(value=0.1, decimals=3)
        self.initialised = False

    def adjust_params(self):
        self.initialised = True
        self.gamma, toe, threshold, self.a = self.gamma_toe[self.config['gamma']]
        knee = self.config['knee']
        knee_point = self.config['knee_point']
        knee_slope = self.config['knee_slope']
        black = self.config['black']
        white = self.config['white']
        scale = self.config['scale']
        # choose function to evaluate
        if self.config['gamma'] == 'hybrid_log':
            func = self.eval_hybrid_log
        elif self.config['gamma'] == 'S-Log':
            func = self.eval_s_log
        elif self.config['gamma'] == 'Canon-Log':
            func = self.eval_canon_log
        else:
            func = self.eval_gamma
        # set function ranges
        self.k_out = 1.0
        self.k_in = 1.0
        self.k_out = 1.0 / func(scale)
        self.k_in = scale
        # make list of in and out values
        in_lo = (-16.0 - black) / (white - black)
        in_hi = (256.0 + 16.0 - black) / (white - black)
        in_val = []
        out_val = []
        # compute first two points (linear slope)
        if toe is None:
            v_out = func((threshold / scale) + 0.0000000001)
            v_in = in_lo
            in_val.append(v_in)
            out_val.append(v_out)
            v_in = threshold / scale
        else:
            v_in = in_lo
            v_out = v_in * toe
            in_val.append(v_in)
            out_val.append(v_out)
            v_in = threshold / scale
            v_out = v_in * toe
        in_val.append(v_in)
        out_val.append(v_out)
        # complicated section needs many points
        x_step = 0.0001
        while v_in < in_hi:
            v_in += x_step
            if knee and v_in >= knee_point:
                # knee section just needs another two endpoints
                v_in = knee_point
                v_out = func(v_in)
                in_val.append(v_in)
                out_val.append(v_out)
                step = max(in_hi - v_in, 0.1)
                in_val.append(v_in + step)
                out_val.append(v_out + (knee_slope * step))
                break
            v_out = func(v_in)
            y_step = abs(v_out - out_val[-1])
            if y_step < 0.005 and x_step < 0.5:
                v_in -= x_step
                x_step *= 2.0
                continue
            if y_step > 0.5 and x_step > 0.005:
                v_in -= x_step
                x_step /= 2.0
                continue
            in_val.append(v_in)
            out_val.append(v_out)
        self.in_val = numpy.array(in_val, dtype=pt_float)
        self.out_val = numpy.array(out_val, dtype=pt_float)
        # scale "linear" values
        self.in_val *= pt_float(white - black)
        self.in_val += pt_float(black)
        # scale gamma corrected values to normal video range
        self.out_val *= pt_float(255.0)
        # send section of curve to function output
        func_frame = self.outframe_pool['function'].get()
        lo = 0
        while lo < len(self.out_val) and self.out_val[lo] < -64:
            lo += 1
        hi = len(self.out_val) - 1
        while hi >= 0 and self.out_val[hi] > 256 + 64:
            hi -= 1
        func_frame.data = numpy.stack((self.in_val[lo:hi+1],
                                       self.out_val[lo:hi+1]))
        func_frame.type = 'func'
        audit = func_frame.metadata.get('audit')
        audit += 'data = GammaFunction({})\n'.format(self.config['gamma'])
        func_frame.metadata.set('audit', audit)
        func_frame.metadata.set(
            'labels', str(['gamma curve', self.config['gamma']]))
        self.send('function', func_frame)

    def eval_hybrid_log(self, v_in):
        v_in *= self.k_in
        if v_in <= 1.0:
            v_out = 0.5 * math.sqrt(v_in)
        else:
            v_out = (0.17883277 * math.log(v_in - 0.28466892)) + 0.55991073
        v_out *= self.k_out
        return v_out

    def eval_s_log(self, v_in):
        v_in *= self.k_in
        v_out = (0.432699 * math.log10(v_in + 0.037584)) + 0.616596 + 0.03
        v_out *= self.k_out
        return v_out

    def eval_canon_log(self, v_in):
        v_in *= self.k_in
        v_out = (0.529136 * math.log10((10.1596 * v_in) + 1.0)) + 0.0730597
        v_out *= self.k_out
        return v_out

    def eval_gamma(self, v_in):
        v_in *= self.k_in
        v_out = v_in ** self.gamma
        v_out = ((1.0 + self.a) * v_out) - self.a
        v_out *= self.k_out
        return v_out

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
        audit += '    range: {}-{}, scale: {}\n'.format(
            self.config['black'], self.config['white'], self.config['scale'])
        if self.config['knee']:
            audit += '    knee at {}, slope {}\n'.format(
                self.config['knee_point'], self.config['knee_slope'])
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

    The ``smooth`` option (present if scipy_ is installed) converts the
    series of data points to a smooth curve using cubic spline interpolation.

    .. _scipy: http://scipy.org/

    ==============  =====  ====
    Config
    ==============  =====  ====
    ``in_vals``     str    List of input values, in increasing order.
    ``out_vals``    str    List of corresponding output values.
    ``inverse``     bool
    ``smooth``      bool   Smooth transform with cubic spline interpolation. Requires scipy_.
    ==============  =====  ====

    """
    outputs = ['output', 'function']    #:

    def initialise(self):
        self.config['in_vals'] = ConfigStr(value='0.0, 255.0')
        self.config['out_vals'] = ConfigStr(value='0.0, 255.0')
        self.config['inverse'] = ConfigBool()
        if interpolate:
            self.config['smooth'] = ConfigBool()
        self.initialised = False

    def adjust_params(self):
        self.initialised = True
        in_vals = eval(self.config['in_vals'])
        out_vals = eval(self.config['out_vals'])
        if len(in_vals) > len(out_vals):
            in_vals = in_vals[:len(out_vals)]
        elif len(out_vals) > len(in_vals):
            out_vals = out_vals[:len(in_vals)]
        self.in_vals = numpy.array(in_vals, dtype=pt_float)
        self.out_vals = numpy.array(out_vals, dtype=pt_float)
        # smooth data
        if interpolate and self.config['smooth'] and len(in_vals) >= 4:
            # extend input to straighten ends of interpolation
            dx0 = (self.in_vals[1] - self.in_vals[0]) / 2.0
            dy0 = (self.out_vals[1] - self.out_vals[0]) / 2.0
            dx1 = (self.in_vals[-1] - self.in_vals[-2]) / 2.0
            dy1 = (self.out_vals[-1] - self.out_vals[-2]) / 2.0
            x = numpy.concatenate((
                [self.in_vals[0]-dx0, self.in_vals[0], self.in_vals[0]+dx0],
                self.in_vals[1:-2],
                [self.in_vals[-1]-dx1, self.in_vals[-1], self.in_vals[-1]+dx1]))
            y = numpy.concatenate((
                [self.out_vals[0]-dy0, self.out_vals[0], self.out_vals[0]+dy0],
                self.out_vals[1:-2],
                [self.out_vals[-1]-dy1, self.out_vals[-1], self.out_vals[-1]+dy1]))
            tck = interpolate.splrep(x, y)
            step = (self.in_vals[-1] - self.in_vals[0]) / 256.0
            x = numpy.arange(
                self.in_vals[0], self.in_vals[-1] + step, step)
            y = interpolate.splev(x, tck)
            self.in_vals = x.astype(pt_float)
            self.out_vals = y.astype(pt_float)
        # send function output
        func_frame = self.outframe_pool['function'].get()
        func_frame.data = numpy.stack((self.in_vals, self.out_vals))
        func_frame.type = 'func'
        audit = func_frame.metadata.get('audit')
        audit += 'data = PiecewiseGammaFunction()\n'
        audit += '    in_vals: {}\n'.format(self.config['in_vals'])
        audit += '    out_vals: {}\n'.format(self.config['out_vals'])
        if interpolate:
            audit += '    smoothing: {}\n'.format(self.config['smooth'])
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
