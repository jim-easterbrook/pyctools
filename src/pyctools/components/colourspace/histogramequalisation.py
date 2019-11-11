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

__all__ = ['HistogramEqualisation']
__docformat__ = 'restructuredtext en'

import cv2
import numpy

from pyctools.core.config import ConfigBool, ConfigEnum, ConfigFloat
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float
from .gammacorrectioncore import apply_transfer_function

class HistogramEqualisation(Transformer):
    """Histogram equalisation.

    Converts the RGB input to luminance and equalises it, then applies
    the same per-pixel gain to the RGB data.

    The ``function`` output emits the transfer function data. It can be
    connected to the
    :py:class:`~pyctools.components.io.plotdata.PlotData` component.

    ============  =====  ====
    Config
    ============  =====  ====
    ``weight_R``  float  RGB to Y matrix red weight.
    ``weight_G``  float  RGB to Y matrix green weight.
    ``weight_B``  float  RGB to Y matrix blue weight.
    ============  =====  ====

    """
    outputs = ['output', 'function']    #:

    def initialise(self):
        self.config['weight_R'] = ConfigFloat(value=0.2126, decimals=4)
        self.config['weight_G'] = ConfigFloat(value=0.7152, decimals=4)
        self.config['weight_B'] = ConfigFloat(value=0.0722, decimals=4)

    def transform(self, in_frame, out_frame):
        self.update_config()
        weight_R = pt_float(self.config['weight_R'])
        weight_G = pt_float(self.config['weight_G'])
        weight_B = pt_float(self.config['weight_B'])
        # get data
        data = in_frame.as_numpy(dtype=pt_float)[:, :, 0:3]
        # calculate pseudo-luminance
        lum_in = numpy.dot(data, numpy.array([weight_R, weight_G, weight_B]))
        # compute normalised histogram
        hist, edges = numpy.histogram(lum_in, bins=64, density=True)
        # generate transfer function by integrating histogram
        gain = 255.0 * 255.0 / float(len(hist))
        acc = 0.0
        x = []
        y = []
        for i in range(len(hist)):
            x.append(edges[i])
            y.append(acc)
            acc += hist[i] * gain
        x.append(edges[-1])
        y.append(acc)
        x = numpy.array(x, dtype=pt_float)
        y = numpy.array(y, dtype=pt_float)
        # equalise luminance
        lum_out = numpy.atleast_3d(lum_in.copy())
        apply_transfer_function(lum_out, x, y)
        # apply same per-pixel gain to image
        out_frame.data = data * lum_out / numpy.atleast_3d(lum_in)
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = HistogramEqualisation(data)\n'
        out_frame.metadata.set('audit', audit)
        # send transfer function
        func_frame = self.outframe_pool['function'].get()
        func_frame.initialise(in_frame)
        func_frame.data = numpy.stack((x, y))
        func_frame.type = 'func'
        audit = func_frame.metadata.get('audit')
        audit += 'data = HistogramEqualisationFunction()\n'
        func_frame.metadata.set('audit', audit)
        self.send('function', func_frame)
        return True
