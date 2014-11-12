#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014  Jim Easterbrook  jim@jim-easterbrook.me.uk
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

"""Gaussian filter generator.

Create `Gaussian filters
<http://en.wikipedia.org/wiki/Gaussian_filter>`_ for use with the
:py:class:`~.resize.Resize` component. This module defines a
:py:class:`GaussianFilter` component and a
:py:func:`GaussianFilterCore` function. You should use one or the
other as follows.

Connecting a :py:class:`GaussianFilter` component's ``output`` to a
:py:class:`~.resize.Resize` component's ``filter`` input allows the
filter to be updated (while the components are running) by changing
the :py:class:`GaussianFilter` config::

    filgen = GaussianFilter()
    cfg = filgen.get_config()
    cfg['xsigma'] = 1.5
    filgen.set_config(cfg)
    resize = Resize()
    filgen.bind('output', resize, 'filter')
    ...
    start(..., filgen, resize, ...)
    ...
    cfg = filgen.get_config()
    cfg['xsigma'] = 1.8
    filgen.set_config(cfg)
    ...

The :py:func:`GaussianFilterCore` function can be used instead to
make a non-reconfigurable resizer::

    resize = Resize()
    resize.filter(GaussianFilterCore(x_sigma=1.5))
    ...
    start(..., resize, ...)
    ...

2-dimensional filters can be produced, but it is usually more
efficient to use two :py:class:`~.resize.Resize` components to process
the two dimensions independently.

"""

from __future__ import print_function

__all__ = ['GaussianFilter']
__docformat__ = 'restructuredtext en'

import math
import time
import sys
if 'sphinx' in sys.modules:
    __all__.append('GaussianFilterCore')

import numpy

from pyctools.core.config import ConfigFloat
from pyctools.core.base import Component
from pyctools.core.frame import Frame

class GaussianFilter(Component):
    """Config:

    ==========  =====  ====
    ``xsigma``  float  Horizontal standard deviation parameter.
    ``ysigma``  float  Vertical standard deviation parameter.
    ==========  =====  ====

    """
    inputs = []

    def initialise(self):
        self.config['xsigma'] = ConfigFloat(min_value=0.0)
        self.config['ysigma'] = ConfigFloat(min_value=0.0)

    def gen_process(self):
        # wait for self.output to be connected
        while self.output.__self__ == self:
            yield 1
            time.sleep(0.01)
        # send first filter coefs
        self.update_config()
        self.make_filter()
        # send more coefs if config changes
        while True:
            yield 1
            time.sleep(0.1)
            if self.update_config():
                self.make_filter()

    def make_filter(self):
        x_sigma = self.config['xsigma']
        y_sigma = self.config['ysigma']
        self.output(GaussianFilterCore(x_sigma=x_sigma, y_sigma=y_sigma))

def GaussianFilterCore(x_sigma=0.0, y_sigma=0.0):
    """

    :keyword float x_sigma: Horizontal standard deviation parameter.

    :keyword float y_sigma: Vertical standard deviation parameter.

    :return: A :py:class:`~pyctools.core.frame.Frame` object containing the
        filter.

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
    result = numpy.empty(y_fil.shape + x_fil.shape, dtype=numpy.float32)
    for y in range(y_fil.shape[0]):
        for x in range(x_fil.shape[0]):
            result[y, x] = x_fil[x] * y_fil[y]
    out_frame = Frame()
    out_frame.data = [result]
    out_frame.type = 'fil'
    audit = out_frame.metadata.get('audit')
    audit += 'data = GaussianFilter()\n'
    if x_sigma != 0.0:
        audit += '    x_sigma: %g\n' % (x_sigma)
    if y_sigma != 0.0:
        audit += '    y_sigma: %g\n' % (y_sigma)
    out_frame.metadata.set('audit', audit)
    return out_frame

def main():
    import logging
    from guild.actor import Actor, actor_method, pipeline, start, stop, wait_for
    class Sink(Actor):
        @actor_method
        def input(self, coefs):
            print(coefs.data)

    logging.basicConfig(level=logging.DEBUG)
    print('GaussianFilter demonstration')
    source = GaussianFilter()
    config = source.get_config()
    config['xsigma'] = 1.7
    source.set_config(config)
    sink = Sink()
    pipeline(source, sink)
    start(source, sink)
    time.sleep(5)
    config['xsigma'] = 2.5
    source.set_config(config)
    time.sleep(5)
    stop(source, sink)
    wait_for(source, sink)
    return 0

if __name__ == '__main__':
    main()
