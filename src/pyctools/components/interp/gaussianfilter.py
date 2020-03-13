#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-20  Pyctools contributors
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

__all__ = ['GaussianFilter']
__docformat__ = 'restructuredtext en'

import math
import sys

import numpy

from pyctools.core.config import ConfigFloat
from pyctools.core.base import Component
from pyctools.core.frame import Frame


class GaussianFilter(Component):
    """Gaussian filter generator component.

    Create a `Gaussian filter
    <http://en.wikipedia.org/wiki/Gaussian_filter>`_ for use with the
    :py:class:`~.resize.Resize` component.

    Connecting a :py:class:`GaussianFilter` component's ``output`` to a
    :py:class:`~.resize.Resize` component's ``filter`` input allows the
    filter to be updated (while the components are running) by changing
    the :py:class:`GaussianFilter` config::

        filgen = GaussianFilter(xsigma=1.5)
        resize = Resize()
        filgen.connect('output', resize.filter)
        ...
        start(..., filgen, resize, ...)
        ...
        filgen.set_config({'xsigma': 1.8})
        ...

    If you don't need to change the configuration after creating the
    :py:class:`~.resize.Resize` component then it's simpler to use a
    :py:class:`GaussianFilterCore` to create a fixed filter.

    2-dimensional filters can be produced by setting both ``xsigma`` and
    ``ysigma``, but it is usually more efficient to use two
    :py:class:`~.resize.Resize` components to process the two dimensions
    independently.

    Config:

    ==========  =====  ====
    ``xsigma``  float  Horizontal standard deviation parameter.
    ``ysigma``  float  Vertical standard deviation parameter.
    ==========  =====  ====

    """
    inputs = []
    with_outframe_pool = False

    def initialise(self):
        self.config['xsigma'] = ConfigFloat(min_value=0.0)
        self.config['ysigma'] = ConfigFloat(min_value=0.0)

    def on_start(self):
        # send first filter coefs
        self.make_filter()

    def on_set_config(self):
        # send more coefs if config changes
        self.make_filter()

    def make_filter(self):
        self.update_config()
        x_sigma = self.config['xsigma']
        y_sigma = self.config['ysigma']
        self.send('output', self.core(x_sigma=x_sigma, y_sigma=y_sigma))

    @classmethod
    def core(cls, x_sigma=0.0, y_sigma=0.0):
        """Gaussian filter generator core.

        Alternative to the :py:class:`GaussianFilter` component that can
        be used to make a non-reconfigurable filter::

            resize = Resize()
            resize.filter(GaussianFilter.core(x_sigma=1.5))
            ...
            start(..., resize, ...)
            ...

        :keyword float x_sigma: Horizontal standard deviation parameter.

        :keyword float y_sigma: Vertical standard deviation parameter.

        :return: A :py:class:`~pyctools.core.frame.Frame` object
            containing the filter.

        """
        def filter_1D(sigma):
            alpha = 1.0 / (2.0 * (max(sigma, 0.0001) ** 2.0))
            coefs = []
            coef = 1.0
            while coef > 0.0001:
                coefs.append(coef)
                coef = math.exp(-(alpha * (float(len(coefs) ** 2))))
            fil_dim = len(coefs) - 1
            result = numpy.zeros(1 + (fil_dim * 2), dtype=numpy.float32)
            for n, coef in enumerate(coefs):
                result[fil_dim - n] = coef
                result[fil_dim + n] = coef
            # normalise result
            result /= result.sum()
            return result

        x_sigma = max(x_sigma, 0.0)
        y_sigma = max(y_sigma, 0.0)
        x_fil = filter_1D(x_sigma)
        y_fil = filter_1D(y_sigma)
        result = numpy.empty(
            [y_fil.shape[0], x_fil.shape[0], 1], dtype=numpy.float32)
        for y in range(y_fil.shape[0]):
            for x in range(x_fil.shape[0]):
                result[y, x, 0] = x_fil[x] * y_fil[y]
        out_frame = Frame()
        out_frame.data = result
        out_frame.type = 'fil'
        sigmas = []
        if x_sigma != 0.0:
            sigmas.append('x_sigma={:g}'.format(x_sigma))
        if y_sigma != 0.0:
            sigmas.append('y_sigma={:g}'.format(y_sigma))
        out_frame.set_audit(
            cls,
            'data = GaussianFilterCoefficients({})\n'.format(','.join(sigmas)))
        return out_frame
