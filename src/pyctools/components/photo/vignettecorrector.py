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

from __future__ import print_function

__all__ = ['VignetteCorrector', 'AnalyseVignette',
           'VignetteCorrectorExp', 'AnalyseVignetteExp']
__docformat__ = 'restructuredtext en'

import math

import numpy
import scipy

from pyctools.core.config import ConfigEnum, ConfigFloat, ConfigInt, ConfigStr
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float


def radius_squared(w, h):
    xc = float(w - 1) / 2.0
    yc = float(h - 1) / 2.0
    index = numpy.mgrid[0:h, 0:w]
    return ((((index[1] - xc) ** 2) + ((index[0] - yc) ** 2)) /
            ((xc ** 2) + (yc ** 2)))


class VignetteCorrector(Transformer):
    """Vignette corrector.

    Adjust the brightness of images with a radially varying gain
    function. This should be applied to 'linear intensity' image data
    before gamma correction is applied.

    The ``r2`` ... ``r8`` parameters set how the correction varies with
    radius^n. The first affects the whole picture, the higher powers
    have more effect at the edges. The :py:class:`AnalyseVignette`
    component can be used to generate an optimised set of values.

    ===========  =====  ====
    Config
    ===========  =====  ====
    ``r2``       float  Amount of radius^2 correction
    ``r4``       float  Amount of radius^4 correction
    ``r6``       float  Amount of radius^6 correction
    ``r8``       float  Amount of radius^8 correction
    ===========  =====  ====

    """

    def initialise(self):
        self.config['r2'] = ConfigFloat(decimals=4)
        self.config['r4'] = ConfigFloat(decimals=4)
        self.config['r6'] = ConfigFloat(decimals=4)
        self.config['r8'] = ConfigFloat(decimals=4)
        self.gain = None

    def transform(self, in_frame, out_frame):
        if self.update_config():
            self.gain = None
        # get data
        data = in_frame.as_numpy(dtype=pt_float)
        # generate correction function
        r2 = self.config['r2']
        r4 = self.config['r4']
        r6 = self.config['r6']
        r8 = self.config['r8']
        h, w = data.shape[:2]
        if self.gain is None or self.gain.shape != [h, w, 1]:
            self.gain = numpy.polyval(
                [r8, r6, r4, r2, 1.0], radius_squared(w, h))
            self.gain = numpy.expand_dims(self.gain, axis=2)
        # apply correction
        out_frame.data = data * self.gain
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = VignetteCorrector(data, {}, {}, {}, {})\n'.format(
            r2, r4, r6, r8)
        out_frame.metadata.set('audit', audit)
        return True


class VignetteCorrectorExp(Transformer):
    """Vignette corrector.

    Adjust the brightness of images with a radially varying gain
    function. This should be applied to 'linear intensity' image data
    before gamma correction is applied.

    The ``mode`` parameter sets the function to use. The ``params``
    value sets how the correction varies with radius. It should be a
    list of numbers whose meaning depends on the function. The
    :py:class:`AnalyseVignetteExp` component can be used to generate
    optimised values.

    ===========  =====  ====
    Config
    ===========  =====  ====
    ``mode``     str    Function to use.
    ``params``   str    Function parameters or coefficients.
    ===========  =====  ====

    """

    def initialise(self):
        self.config['mode'] = ConfigEnum(choices=('power', 'poly2', 'poly3'))
        self.config['params'] = ConfigStr(value='[1.0, 0.5]')
        self.gain = None

    @staticmethod
    def power(x, a, b):
        return 1.0 + (a * (x ** b))

    @staticmethod
    def poly2(x, a, b):
        return 1.0 + (a * (x ** 2)) + (b * (x ** 4))

    @staticmethod
    def poly3(x, a, b, c):
        return 1.0 + (a * (x ** 2)) + (b * (x ** 4)) + (c * (x ** 6))

    def transform(self, in_frame, out_frame):
        if self.update_config():
            self.gain = None
        mode = self.config['mode']
        params = eval(self.config['params'])
        # get data
        data = in_frame.as_numpy(dtype=pt_float)
        # generate correction function
        h, w = data.shape[:2]
        if self.gain is None or self.gain.shape != [h, w, 1]:
            func = getattr(self, mode)
            self.gain = func(radius_squared(w, h), *params)
            self.gain = numpy.expand_dims(self.gain, axis=2)
        # apply correction
        out_frame.data = data * self.gain
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = VignetteCorrectorExp(data, {}, {})\n'.format(
            mode, str(params))
        out_frame.metadata.set('audit', audit)
        return True


class AnalyseVignette(Transformer):
    """Vignette analysis.

    Measures the average luminance of 50 circular bands of an input grey
    image, then calculates the optimum ``r2`` ... ``rn`` parameters to
    correct it. This is easier to use than trying to set the parameters
    manually.

    The ``order`` parameter can be used to adjust the number of
    coefficients produced. It is probably a good idea to use the
    smallest number that gives acceptable results.

    ``log_eps`` controls the fitting of the polynomial. If it is too
    negative the polynomial will be a very tight fit but the
    coefficients may have very large values and change wildly when there
    is a small change in input. See :py:func:`numpy.polyfit` for more
    detail.

    The ``function`` output emits the measured and fitted gain
    functions. It can be connected to a
    :py:class:`~pyctools.components.io.plotdata.PlotData` component.

    ===========  =====  ====
    Config
    ===========  =====  ====
    ``order``    int    Number of ``r`` parameters to generate.
    ``log_eps``  float  Base 10 logarithm of relative precision.
    ===========  =====  ====

    """
    outputs = ['output', 'function']

    def initialise(self):
        self.config['order'] = ConfigInt(value=3, min_value=1)
        self.config['log_eps'] = ConfigFloat(value=-4, decimals=1)

    def transform(self, in_frame, out_frame):
        self.update_config()
        # get data
        data = in_frame.as_numpy(dtype=pt_float)
        # compute normalised radius
        h, w = data.shape[:2]
        r = numpy.sqrt(radius_squared(w, h))
        # calculate required gain for each radial band
        bands = 50
        x = []
        y = []
        w = []
        hi = 0.0
        for i in range(bands):
            x.append(float(i) / float(bands - 1))
            lo = hi
            hi = (float(i) + 0.5) / float(bands - 1)
            mask = numpy.logical_and(r >= lo, r < hi)
            mean = numpy.mean(data[mask])
            std = numpy.std(data[mask])
            w.append(((1.1 * bands) - i) / std)
            if i == 0:
                norm_factor = mean
            y.append(norm_factor / mean)
        x = numpy.array(x)
        y = numpy.array(y)
        w = numpy.array(w)
        # boost weighting at centre
        w[0] *= 100.0
        # fit a polynomial in x^2 to the required gain
        order = self.config['order']
        rcond = float(bands) * (10.0 ** self.config['log_eps'])
        fit = numpy.polyfit(x * x, y, order, rcond=rcond, w=w)
        fit /= fit[-1]
        # print out parameters
        for i in range(order):
            k = fit[-(i+2)]
            print('r{} = {:.4f}'.format((i + 1) * 2, k))
        # send plottable data
        func_frame = self.outframe_pool['function'].get()
        func_frame.data = numpy.stack((x, y, numpy.polyval(fit, x * x)))
        func_frame.type = 'func'
        func_frame.metadata.set('labels', repr(['radius', 'measured', 'fitted']))
        audit = func_frame.metadata.get('audit')
        audit += 'data = VignetteCorrectorFunction()\n'
        func_frame.metadata.set('audit', audit)
        self.send('function', func_frame)
        return True


class AnalyseVignetteExp(Transformer):
    """Vignette analysis.

    Measures the average luminance of 50 circular bands of an input grey
    image, then calculates the optimum function parameters to correct
    it.

    The ``mode`` configuration selects the function to fit. If set to
    ``measure`` or ``inv_measure`` no function is fitted. In
    ``inv_measure`` mode the output shows the vignetting instead of the
    required correction.

    The ``function`` output emits the measured and fitted gain
    functions. It can be connected to a
    :py:class:`~pyctools.components.io.plotdata.PlotData` component.

    ============  =====  ====
    Config
    ============  =====  ====
    ``mode``      str    Function to fit.
    ============  =====  ====

    """
    outputs = ['output', 'function']

    def initialise(self):
        self.config['mode'] = ConfigEnum(
            choices=('measure', 'inv_measure', 'power', 'poly2', 'poly3'))

    @staticmethod
    def power(x, a, b, c):
        return (1.0 + (a * (x ** b))) * c

    def transform(self, in_frame, out_frame):
        self.update_config()
        mode = self.config['mode']
        # get data
        data = in_frame.as_numpy(dtype=numpy.float64)
        # compute normalised radius
        h, w = data.shape[:2]
        r = numpy.sqrt(radius_squared(w, h))
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
            fit_func = getattr(self, mode)
            popt_linear, pcov_linear = scipy.optimize.curve_fit(
                fit_func, x, y, sigma=sigma)
            for n, value in enumerate(popt_linear[:-1]):
                print('param {}: {}'.format(n, value))
        # send plottable data
        func_frame = self.outframe_pool['function'].get()
        plots = [x, y / y[0]]
        labels = ['radius', 'measured']
        if mode not in ('measure', 'inv_measure'):
            plots.append(fit_func(x, *popt_linear) / y[0])
            labels.append(mode)
        func_frame.data = numpy.stack(plots)
        func_frame.type = 'func'
        func_frame.metadata.set('labels', repr(labels))
        audit = func_frame.metadata.get('audit')
        audit += 'data = VignetteCorrectorFunction()\n'
        func_frame.metadata.set('audit', audit)
        self.send('function', func_frame)
        return True
