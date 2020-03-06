#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2016-20  Pyctools contributors
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

__all__ = ['VignetteCorrector', 'AnalyseVignette']
__docformat__ = 'restructuredtext en'

import inspect

import numpy
import scipy.optimize

from pyctools.core.config import (
    ConfigBool, ConfigEnum, ConfigFloat, ConfigInt, ConfigStr)
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float


def radius(w, h):
    xc = float(w - 1) / 2.0
    yc = float(h - 1) / 2.0
    r2 = (xc ** 2) + (yc ** 2)
    index = numpy.mgrid[0 : h // 2, 0 : w // 2].astype(numpy.float64)
    quad = numpy.sqrt((((index[1] + 0.5) ** 2) + ((index[0] + 0.5) ** 2)) / r2)
    result = numpy.ndarray((h, w), dtype=numpy.float64)
    result[h // 2 : h, w // 2 : w] = quad
    result[h // 2 : h, 0 : w // 2] = quad[:, ::-1]
    result[0 : h // 2, w // 2 : w] = quad[::-1, :]
    result[0 : h // 2, 0 : w // 2] = quad[::-1, ::-1]
    return result


class power(object):
    "1.0 + (a * (r ^ b))"

    @staticmethod
    def process(x, a, b):
        return 1.0 + (a * (x ** b))

    @staticmethod
    def analyse(x, a, b, c):
        return power.process(x, a, b) * c

    kwds = {}


class poly2(object):
    "1.0 + (a * (r ^ 2)) + (b * (r ^ 4))"

    @staticmethod
    def process(x, a, b):
        return 1.0 + (a * (x ** 2)) + (b * (x ** 4))

    @staticmethod
    def analyse(x, a, b, c):
        return poly2.process(x, a, b) * c

    kwds = {}


class poly3(object):
    "1.0 + (a * (r ^ 2)) + (b * (r ^ 4)) + (c * (r ^ 6))"

    @staticmethod
    def process(x, a, b, c):
        return 1.0 + (a * (x ** 2)) + (b * (x ** 4)) + (c * (x ** 6))

    @staticmethod
    def analyse(x, a, b, c, d):
        return poly3.process(x, a, b, c) * d

    kwds = {}


class lin2(object):
    "2-segment piecewise linear"

    @staticmethod
    def process(x, a, b, c):
        s0 = (b - 1.0) / a
        s1 = (c - b) / (1 - a)
        f = x.flatten()
        return numpy.piecewise(
            f, (f <= a), (lambda x: 1.0 + (x * s0),
                          lambda x: b + ((x - a) * s1))
            ).reshape(x.shape)

    @staticmethod
    def analyse(x, a, b, c, d):
        return lin2.process(x, a, b, c) * d

    kwds = {'p0': (0.5, 1.2, 1.4, 1.0),
            'bounds': ((0.0, 0.0, 0.0, -numpy.inf),
                       (1.0, 2.0, 2.0, numpy.inf))
            }


class invlin2(object):
    "inverse 2-segment piecewise linear"

    @staticmethod
    def process(x, a, b, c):
        return 1.0 / lin2.process(x, a, 1.0 / b, 1.0 / c)

    @staticmethod
    def analyse(x, a, b, c, d):
        return invlin2.process(x, a, b, c) * d

    kwds = lin2.kwds


class lin3(object):
    "3-segment piecewise linear"

    @staticmethod
    def process(x, a, b, c, d, e):
        if b < a:
            a, b = b, a
            c, d = d, c
        s0 = (c - 1.0) / a
        s1 = (d - c) / (b - a)
        s2 = (e - d) / (1 - b)
        f = x.flatten()
        return numpy.piecewise(
            f, (f <= a, f >= b), (lambda x: 1.0 + (x * s0),
                                  lambda x: d + ((x - b) * s2),
                                  lambda x: c + ((x - a) * s1))
            ).reshape(x.shape)

    @staticmethod
    def analyse(x, a, b, c, d, e, f):
        return lin3.process(x, a, b, c, d, e) * f

    kwds = {'p0': (0.3, 0.6, 1.2, 1.3, 1.4, 1.0),
            'bounds': ((0.0, 0.0, 0.01, 0.01, 0.01, -numpy.inf),
                       (1.0, 1.0, 2.0, 2.0, 2.0, numpy.inf))
            }


class invlin3(object):
    "inverse 3-segment piecewise linear"

    @staticmethod
    def process(x, a, b, c, d, e):
        return 1.0 / lin3.process(x, a, b, 1.0 / c, 1.0 / d, 1.0 / e)

    @staticmethod
    def analyse(x, a, b, c, d, e, f):
        return invlin3.process(x, a, b, c, d, e) * f

    kwds = lin3.kwds


functions = {}
for class_ in power, poly2, poly3, lin2, lin3, invlin2, invlin3:
    functions[class_.__name__] = class_


class VignetteCorrector(Transformer):
    """Vignette corrector.

    Adjust the brightness of images with a radially varying gain
    function. This should be applied to 'linear intensity' image data
    before gamma correction is applied.

    The ``mode`` parameter sets the function to use. The ``param_n``
    values set how the correction varies with radius. Their meaning
    depends on the function. The :py:class:`AnalyseVignette` component
    can be used to generate optimised values.

    ===========  =====  ====
    Config
    ===========  =====  ====
    ``mode``     str    Function to use. Possible values: {}.
    ``param_0``  float  First function parameter.
    ``param_1``  float  Second function parameter.
    ``param_2``  float  Third function parameter.
    ``param_3``  float  Fourth function parameter.
    ``param_4``  float  Fifth function parameter.
    ===========  =====  ====

    """

    __doc__ = __doc__.format(
        ', '.join(["``'" + x + "'``" for x in functions]))

    def initialise(self):
        self.config['mode'] = ConfigEnum(choices=list(functions.keys()))
        self.config['param_0'] = ConfigFloat()
        self.config['param_1'] = ConfigFloat()
        self.config['param_2'] = ConfigFloat()
        self.config['param_3'] = ConfigFloat()
        self.config['param_4'] = ConfigFloat()
        self.gain = None

    def on_set_config(self):
        self.gain = None

    def transform(self, in_frame, out_frame):
        self.update_config()
        mode = self.config['mode']
        params = (self.config['param_0'],
                  self.config['param_1'],
                  self.config['param_2'],
                  self.config['param_3'],
                  self.config['param_4'])
        func = functions[mode].process
        arg_spec = inspect.getargspec(func)
        params = params[:len(arg_spec.args)-1]
        # get data
        data = in_frame.as_numpy(dtype=pt_float)
        # generate correction function
        h, w = data.shape[:2]
        if self.gain is None or self.gain.shape != [h, w, 1]:
            quad = radius(w, h)[h // 2 : h, w // 2 : w]
            quad = func(quad, *params).astype(pt_float)
            self.gain = numpy.ndarray((h, w, 1), dtype=pt_float)
            self.gain[h // 2 : h, w // 2 : w, 0] = quad
            self.gain[h // 2 : h, 0 : w // 2, 0] = quad[:, ::-1]
            self.gain[0 : h // 2, w // 2 : w, 0] = quad[::-1, :]
            self.gain[0 : h // 2, 0 : w // 2, 0] = quad[::-1, ::-1]
        # apply correction
        out_frame.data = data * self.gain
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = VignetteCorrector(data, {})\n'.format(mode)
        audit += '    function: {}\n'.format(functions[mode].__doc__)
        for n, value in enumerate(params):
            audit += '    {} = {}\n'.format(chr(ord('a') + n), value)
        out_frame.metadata.set('audit', audit)
        return True


class AnalyseVignette(Transformer):
    """Vignette analysis.

    Measures the average luminance of 50 circular bands of an input grey
    image, then calculates the optimum function parameters to correct
    it.

    The ``mode`` configuration selects the function to fit. If set to
    ``measure`` or ``inv_measure`` no function is fitted. In
    ``inv_measure`` mode the output shows the vignetting instead of the
    required correction. Available functions are:

{}

    The ``function`` output emits the measured and fitted gain values.
    It can be connected to a
    :py:class:`~pyctools.components.io.plotdata.PlotData` component.

    The ``plot...`` parameters can be used to control the plot's
    appearance. Running the component network several times with
    different options allows quite complex plots to be built up.

    =======================  =====  ====
    Config
    =======================  =====  ====
    ``mode``                 str    Function to fit. Possible values: {}.
    ``method``               str    Curve fitting method: ``lm``, ``trf``, or ``dogbox``.
    ``plot_measurement``     bool   Include the measured input in the plot.
    ``plot_error``           bool   Include the residual error in the plot.
    ``plot_label_measured``  str    Label for the 'measured' plot.
    ``plot_label_fitted``    str    Label for the 'fitted' plot. If left blank ``mode`` is used.
    =======================  =====  ====

    """

    __doc__ = __doc__.format(
        '\n\n'.join(['    {}\n        ``{}``'.format(x.__name__, x.__doc__)
                     for x in functions.values()]),
        ', '.join(["``'" + x + "'``"
                   for x in ['measure', 'inv_measure'] + list(functions)])
        )
    outputs = ['output', 'function']    #:

    def initialise(self):
        self.config['mode'] = ConfigEnum(
            choices=['measure', 'inv_measure'] + list(functions))
        self.config['method'] = ConfigEnum(choices=('lm', 'trf', 'dogbox'))
        self.config['plot_measurement'] = ConfigBool(value=True)
        self.config['plot_error'] = ConfigBool(value=True)
        self.config['plot_label_measured'] = ConfigStr(value='measured')
        self.config['plot_label_fitted'] = ConfigStr(value='')

    def transform(self, in_frame, out_frame):
        self.update_config()
        mode = self.config['mode']
        # get data
        data = in_frame.as_numpy(dtype=numpy.float64)
        # compute normalised radius
        h, w = data.shape[:2]
        r = radius(w, h)
        # calculate required gain for each radial band
        if mode != 'inv_measure':
            data = 1.0 / data
        bands = 50
        x = []
        y = []
        sigma = []
        hi = 0.0
        for i in range(bands):
            lo = hi
            hi = (float(i) + 0.5) / float(bands - 1)
            mask = numpy.logical_and(r >= lo, r < hi)
            x.append(numpy.mean(r[mask]))
            y.append(numpy.mean(data[mask]))
            sigma.append(numpy.std(data[mask]))
        x = numpy.array(x)
        y = numpy.array(y)
        sigma = numpy.array(sigma)
        # fit a function to the required gain
        if mode in ('measure', 'inv_measure'):
            pass
        else:
            fit_func = functions[mode].analyse
            method = self.config['method']
            try:
                popt_linear, pcov_linear = scipy.optimize.curve_fit(
                    fit_func, x, y, sigma=sigma, method=method,
                    **functions[mode].kwds)
                for n, value in enumerate(popt_linear[:-1]):
                    print('param {}: {}'.format(n, value))
            except Exception as ex:
                print(method, str(ex))
                mode = 'measure'
        # send plottable data
        func_frame = self.outframe_pool['function'].get()
        plots = [x]
        labels = ['radius']
        if self.config['plot_measurement']:
            plots.append(y / y[0])
            labels.append(self.config['plot_label_measured'])
        if mode not in ('measure', 'inv_measure'):
            d = fit_func(x, *popt_linear)
            plots.append(d / y[0])
            labels.append(self.config['plot_label_fitted'] or mode)
            e = d / y
            print('Peak-peak error:', max(e) - min(e))
            if self.config['plot_measurement']:
                plots.append(e)
                labels.append('error')
        func_frame.data = numpy.stack(plots)
        func_frame.type = 'func'
        func_frame.metadata.set('labels', repr(labels))
        audit = func_frame.metadata.get('audit')
        audit += 'data = VignetteCorrectorFunction()\n'
        func_frame.metadata.set('audit', audit)
        self.send('function', func_frame)
        return True
