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

from __future__ import print_function

__all__ = ['VignetteCorrector', 'AnalyseVignette']
__docformat__ = 'restructuredtext en'

import math

import numpy

from pyctools.core.config import ConfigEnum, ConfigFloat, ConfigInt
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float

class VignetteCorrector(Transformer):
    """Vignette corrector.

    Adjust the brightness of images with a radially varying gain
    function. This should be applied to 'linear intensity' image data
    before gamma correction is applied.

    The ``range`` config item specifies the input and output video
    ranges. It can be either ``'studio'`` (16..235) or ``'computer'``
    (0..255).

    The ``r1`` ... ``r4`` parameters set how the correction varies with
    radius^n. The first affects the whole picture, the higher powers
    have more effect at the edges. The :py:class:`AnalyseVignette`
    component can be used to generate an optimised set of values.

    ===========  =====  ====
    Config
    ===========  =====  ====
    ``range``    str    Nominal black and white levels. Can be ``'studio'`` or ``'computer'``.
    ``r1``       float  Amount of radius correction
    ``r2``       float  Amount of radius^2 correction
    ``r3``       float  Amount of radius^3 correction
    ``r4``       float  Amount of radius^4 correction
    ===========  =====  ====

    """

    def initialise(self):
        self.config['range'] = ConfigEnum(('studio', 'computer'))
        self.config['r1'] = ConfigFloat(decimals=4)
        self.config['r2'] = ConfigFloat(decimals=4)
        self.config['r3'] = ConfigFloat(decimals=4)
        self.config['r4'] = ConfigFloat(decimals=4)
        self.gain = None

    def transform(self, in_frame, out_frame):
        if self.update_config():
            self.gain = None
        # get data
        data = in_frame.as_numpy(dtype=pt_float, copy=True)
        # generate correction function
        r1 = self.config['r1']
        r2 = self.config['r2']
        r3 = self.config['r3']
        r4 = self.config['r4']
        h, w = data.shape[:2]
        if self.gain is None or self.gain.shape != [h, w, 1]:
            xc = float(w - 1) / 2.0
            yc = float(h - 1) / 2.0
            r0 = math.sqrt((xc ** 2) + (yc ** 2))
            index = numpy.mgrid[0:h, 0:w].astype(pt_float)
            y = (index[0] - pt_float(yc)) / pt_float(r0)
            x = (index[1] - pt_float(xc)) / pt_float(r0)
            r = numpy.sqrt((x ** 2) + (y ** 2))
            self.gain = ((r * pt_float(r1)) + ((r ** 2) * pt_float(r2)) +
                         ((r ** 3) * pt_float(r3)) + ((r ** 4) * pt_float(r4)) +
                         pt_float(1.0))
            self.gain = numpy.expand_dims(self.gain, axis=2)
        # subtract black level
        if self.config['range'] == 'studio':
            data -= pt_float(16.0)
        # apply correction
        data *= self.gain
        # restore black level
        if self.config['range'] == 'studio':
            data += pt_float(16.0)
        out_frame.data = data
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = VignetteCorrector(data, {}, {}, {}, {})\n'.format(
            r1, r2, r3, r4)
        out_frame.metadata.set('audit', audit)
        return True


class AnalyseVignette(Transformer):
    """Vignette analysis.

    Measures the average luminance of 50 circular bands of an input grey
    image, then calculates the optimum ``r1`` ... ``rn`` parameters to
    correct it. This is easier to use than trying to set the parameters
    manually.

    The ``order`` parameter can be used to adjust the number of
    coefficients produced. It is probably a good idea to use the
    smallest number that gives acceptable results.

    ===========  =====  ====
    Config
    ===========  =====  ====
    ``range``    str    Nominal black and white levels. Can be ``'studio'`` or ``'computer'``.
    ``order``    int    Number of ``r`` parameters to generate.
    ===========  =====  ====

    """

    def initialise(self):
        self.config['range'] = ConfigEnum(('studio', 'computer'))
        self.config['order'] = ConfigInt(value=3, min_value=1)

    def transform(self, in_frame, out_frame):
        self.update_config()
        # get data
        data = in_frame.as_numpy(dtype=pt_float, copy=True)
        # subtract black level
        if self.config['range'] == 'studio':
            data -= pt_float(16.0)
        # compute normalised radius
        h, w = data.shape[:2]
        xc = float(w - 1) / 2.0
        yc = float(h - 1) / 2.0
        r0 = math.sqrt((xc ** 2) + (yc ** 2))
        index = numpy.mgrid[0:h, 0:w].astype(pt_float)
        y = (index[0] - pt_float(yc)) / pt_float(r0)
        x = (index[1] - pt_float(xc)) / pt_float(r0)
        r = numpy.sqrt((x ** 2) + (y ** 2))
        # calculate mean of each radial band
        bands = 50
        x = []
        mean = []
        for i in range(bands):
            x.append(float(i) / float(bands - 1))
            lo = (float(i) - 0.5) / float(bands - 1)
            hi = (float(i) + 0.5) / float(bands - 1)
            mask = numpy.logical_or(r < lo, r >= hi)
            mean.append(numpy.ma.array(data, mask=mask).mean())
        # calculate required gain for each radial band
        norm_factor = mean[0]
        y = []
        for i, value in enumerate(mean):
            y.append(norm_factor / mean[i])
        # fit a polynomial to the required gain
        order = self.config['order']
        fit = numpy.polyfit(x, y, order)
        # print out parameters
        for i in range(order):
            k = fit[-(i+2)] / fit[-1]
            print('r{} = {}'.format(i+1, k))
        return True
