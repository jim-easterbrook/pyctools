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

"""Interpolator filter generator.

Create filters for use with the :py:class:`~.resize.Resize` component.
This module defines a :py:class:`FilterGenerator` component and a
:py:func:`FilterGeneratorCore` function. You should use one or the
other as follows.

Connecting a :py:class:`FilterGenerator` component's ``output`` to a
:py:class:`~.resize.Resize` component's ``filter`` input allows the
filter to be updated (while the components are running) by changing
the :py:class:`FilterGenerator` config::

    filgen = FilterGenerator(xup=2, xaperture=16)
    resize = Resize(xup=2)
    filgen.bind('output', resize, 'filter')
    ...
    start(..., filgen, resize, ...)
    ...
    cfg = filgen.get_config()
    cfg['xaperture'] = 8
    filgen.set_config(cfg)
    ...

The :py:func:`FilterGeneratorCore` function can be used instead to
make a non-reconfigurable resizer::

    resize = Resize(xup=2)
    resize.filter(FilterGeneratorCore(x_up=2, x_aperture=16))
    ...
    start(..., resize, ...)
    ...

The filter is a Hamming windowed sinc function. Its cut frequency is
set to the "Nyquist limit" (half the sampling frequency) for the input
or output sampling frequency, whichever is the lower. This cut
frequency can be adjusted with the ``xcut`` and ``ycut``
configuration.

2-dimensional filters can be produced, but it is usually more
efficient to use two :py:class:`~.resize.Resize` components to process
the two dimensions independently.

"""

from __future__ import print_function

__all__ = ['FilterGenerator']
__docformat__ = 'restructuredtext en'

import math
import time
import sys
if 'sphinx' in sys.modules:
    __all__.append('FilterGeneratorCore')

from guild.actor import *
import numpy

from pyctools.core.config import ConfigInt
from pyctools.core.base import Component
from pyctools.core.frame import Frame

class FilterGenerator(Component):
    """Config:

    =============  ===  ====
    ``xup``        int  Horizontal up-conversion factor.
    ``xdown``      int  Horizontal down-conversion factor.
    ``xaperture``  int  Horizontal filter aperture.
    ``xcut``       int  Adjust horizontal cut frequency. Default is 100%.
    ``yup``        int  Vertical up-conversion factor.
    ``ydown``      int  Vertical down-conversion factor.
    ``yaperture``  int  Vertical filter aperture.
    ``ycut``       int  Adjust vertical cut frequency. Default is 100%.
    =============  ===  ====

    """
    inputs = []

    def initialise(self):
        self.config['xup'] = ConfigInt(min_value=1)
        self.config['xdown'] = ConfigInt(min_value=1)
        self.config['xaperture'] = ConfigInt(min_value=1)
        self.config['xcut'] = ConfigInt(min_value=1, value=100)
        self.config['yup'] = ConfigInt(min_value=1)
        self.config['ydown'] = ConfigInt(min_value=1)
        self.config['yaperture'] = ConfigInt(min_value=1)
        self.config['ycut'] = ConfigInt(min_value=1, value=100)

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
        x_up = self.config['xup']
        x_down = self.config['xdown']
        x_ap = self.config['xaperture']
        x_cut = self.config['xcut']
        y_up = self.config['yup']
        y_down = self.config['ydown']
        y_ap = self.config['yaperture']
        y_cut = self.config['ycut']
        self.output(FilterGeneratorCore(
            x_up=x_up, x_down=x_down, x_ap=x_ap, x_cut=x_cut,
            y_up=y_up, y_down=y_down, y_ap=y_ap, y_cut=y_cut))

def FilterGeneratorCore(x_up=1, x_down=1, x_ap=1, x_cut=100,
                        y_up=1, y_down=1, y_ap=1, y_cut=100):
    """

    :keyword int x_up: Horizontal up-conversion factor.

    :keyword int x_down: Horizontal down-conversion factor.

    :keyword int x_ap: Horizontal filter aperture.

    :keyword int x_cut: Horizontal cut frequency adjustment.

    :keyword int y_up: Vertical up-conversion factor.

    :keyword int y_down: Vertical down-conversion factor.

    :keyword int y_ap: Vertical filter aperture.

    :keyword int y_cut: Vertical cut frequency adjustment.

    :return: A :py:class:`~pyctools.core.frame.Frame` object containing the
        filter.

    """
    def filter_1D(up, down, ap, cut_adj):
        nyquist_freq = float(min(up, down)) / float(2 * up * down)
        cut_adj = float(cut_adj) / 100.0
        coefs = []
        n = 1
        while True:
            theta_1 = float(n) * math.pi * 2.0 * nyquist_freq
            theta_2 = theta_1 * 2.0 / float(ap)
            if theta_2 >= math.pi:
                break
            theta_1 *= cut_adj
            coef = math.sin(theta_1) / theta_1
            win = 0.5 * (1.0 + math.cos(theta_2))
            coef = coef * win
            if abs(coef) < 1.0e-16:
                coef = 0.0
            coefs.append(coef)
            n += 1
        fil_dim = len(coefs)
        result = numpy.ones(1 + (fil_dim * 2), dtype=numpy.float32)
        n = 1
        for coef in coefs:
            result[fil_dim - n] = coef
            result[fil_dim + n] = coef
            n += 1
        # normalise gain of each phase
        phases = (up * down) // min(up, down)
        for n in range(phases):
            result[n::phases] /= result[n::phases].sum()
        result /= float(phases)
        return result

    x_up = max(x_up, 1)
    x_down = max(x_down, 1)
    x_ap = max(x_ap, 1)
    x_cut = max(x_cut, 1)
    y_up = max(y_up, 1)
    y_down = max(y_down, 1)
    y_ap = max(y_ap, 1)
    y_cut = max(y_cut, 1)
    x_fil = filter_1D(x_up, x_down, x_ap, x_cut)
    y_fil = filter_1D(y_up, y_down, y_ap, y_cut)
    result = numpy.empty(y_fil.shape + x_fil.shape, dtype=numpy.float32)
    for y in range(y_fil.shape[0]):
        for x in range(x_fil.shape[0]):
            result[y, x] = x_fil[x] * y_fil[y]
    out_frame = Frame()
    out_frame.data = [result]
    out_frame.type = 'fil'
    audit = out_frame.metadata.get('audit')
    audit += 'data = FilterGenerator()\n'
    if x_up != 1 or x_down != 1 or x_ap != 1:
        audit += '    x_up: %d, x_down: %d, x_ap: %d, x_cut: %d\n' % (
            x_up, x_down, x_ap, x_cut)
    if y_up != 1 or y_down != 1 or y_ap != 1:
        audit += '    y_up: %d, y_down: %d, y_ap: %d, y_cut: %d\n' % (
            y_up, y_down, y_ap, y_cut)
    out_frame.metadata.set('audit', audit)
    return out_frame

def main():
    import logging
    import time
    class Sink(Actor):
        @actor_method
        def input(self, coefs):
            print(coefs.data)

    logging.basicConfig(level=logging.DEBUG)
    print('FilterGenerator demonstration')
    source = FilterGenerator()
    config = source.get_config()
    config['xup'] = 2
    config['xaperture'] = 8
    source.set_config(config)
    sink = Sink()
    pipeline(source, sink)
    start(source, sink)
    time.sleep(5)
    config['xaperture'] = 4
    source.set_config(config)
    time.sleep(5)
    stop(source, sink)
    wait_for(source, sink)
    return 0

if __name__ == '__main__':
    main()
