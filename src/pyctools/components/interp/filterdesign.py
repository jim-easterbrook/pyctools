#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2018  Pyctools contributors
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

__all__ = ['FilterDesign']
__docformat__ = 'restructuredtext en'

from collections import OrderedDict
import math

import numpy
from scipy import interpolate

from pyctools.core.config import ConfigBool, ConfigEnum, ConfigFloat, ConfigInt, ConfigStr
from pyctools.core.base import Component
from pyctools.core.frame import Frame
from pyctools.core.types import pt_float, pt_complex

class FilterDesign(Component):
    """Generate a 1-D filter from an ideal response.

    The response is specified as a series of normalised frequency values
    (in the range 0.0 to 0.5), corresponding gain values, usually in the
    range 0.0 to 1.0, and (optionally) corresponding weight values. A
    filter is generated that minimises the weighted square of the
    deviation from this ideal response.

    The weight values are a measure of how much you care about the
    response at different frequencies. For example, you may want "flat"
    pass bands and stop bands, but not care too much about the
    transition band.

    The ``response`` output emits the ideal and actual filter responses.
    It can be connected to the
    :py:class:`~pyctools.components.io.plotdata.PlotData` component.

    The ``interp`` option selects the function used to convert the
    series of response points to a continuous function, before
    calculating the filter coefficients. See
    :py:class:`scipy:scipy.interpolate.interp1d` for more detail.

    ==============  =====  ====
    Config
    ==============  =====  ====
    ``frequency``   str    List of frequency values, in increasing order.
    ``gain``        str    List of corresponding gain values.
    ``weight``      str    List of corresponding weight values. Default is unity.
    ``aperture``    int    The number of filter coefficients.
    ``interp``      str    Interpolation function.  Possible values: {}
    ``direction``   str    Direction of filter. Possible values: horizontal, vertical.
    ==============  =====  ====

    """
    inputs = []
    outputs = ['filter', 'response']    #:
    with_outframe_pool = False
    interp_list = ('linear', 'nearest', 'zero', 'slinear', 'quadratic', 'cubic')
    __doc__ = __doc__.format(', '.join(["``'" + x + "'``" for x in interp_list]))

    def initialise(self):
        self.config['frequency'] = ConfigStr(value='0.0, 0.5')
        self.config['gain'] = ConfigStr(value='1.0, 0.0')
        self.config['weight'] = ConfigStr()
        self.config['aperture'] = ConfigInt(value=9, min_value=3)
        self.config['interp'] = ConfigEnum(choices=(self.interp_list))
        self.config['direction'] = ConfigEnum(choices=('horizontal', 'vertical'))

    def on_start(self):
        # send first filter coefs
        self.make_filter()

    def on_set_config(self):
        # send more coefs if config changes
        self.make_filter()

    def make_filter(self):
        self.update_config()
        freq_vals = eval(self.config['frequency'])
        gain_vals = eval(self.config['gain'])
        if len(freq_vals) != len(gain_vals):
            self.logger.warning(
                'frequency and gain lists are of different length')
            freq_vals = freq_vals[:len(gain_vals)]
            gain_vals = gain_vals[:len(freq_vals)]
        if self.config['weight']:
            wgt_vals = eval(self.config['weight'])
            if len(wgt_vals) != len(gain_vals):
                self.logger.warning(
                    'frequency and weight lists are of different length')
                wgt_vals = wgt_vals[:len(gain_vals)]
                gain_vals = gain_vals[:len(wgt_vals)]
                freq_vals = freq_vals[:len(gain_vals)]
            wgt_vals = numpy.array(wgt_vals, dtype=pt_float)
        freq_vals = numpy.array(freq_vals, dtype=pt_float)
        gain_vals = numpy.array(gain_vals, dtype=pt_float)
        aperture = self.config['aperture']
        # how much oversampling needed
        pad_len = 256
        while pad_len < aperture * 4:
            pad_len *= 2
        # interpolate ideal response
        int_freq = numpy.linspace(0.0, 0.5, pad_len + 1).astype(pt_float)
        interp_func = interpolate.interp1d(
            freq_vals, gain_vals, kind=self.config['interp'],
            bounds_error=False, fill_value='extrapolate')
        int_gain = interp_func(int_freq).astype(pt_float)
        # interpolate weight
        if self.config['weight']:
            interp_func = interpolate.interp1d(
                freq_vals, wgt_vals, kind=self.config['interp'],
                bounds_error=False, fill_value='extrapolate')
            int_wgt = interp_func(int_freq).astype(pt_float)
        else:
            int_wgt = numpy.ones((pad_len + 1,), dtype=pt_float)
        # 'DC' and 'half fs' gain are always important
        int_wgt_copy = int_wgt.copy()
        int_wgt[0] = numpy.amax(int_wgt) * pad_len
        int_wgt[pad_len] = int_wgt[0]
        # compute response matrices
        W2 = numpy.empty((pad_len * 2,), dtype=pt_float)
        W2[:pad_len + 1] = int_wgt
        W2[pad_len + 1:] = int_wgt[pad_len - 1:0:-1]
        W2 = W2 ** 2
        W2R = numpy.empty((pad_len * 2,), dtype=pt_float)
        W2R[:pad_len + 1] = int_gain
        W2R[pad_len + 1:] = int_gain[pad_len - 1:0:-1]
        W2R *= W2
        W2 = numpy.fft.ifft(W2)
        W2R = numpy.fft.ifft(W2R)
        # compute matrices to solve
        MtM = numpy.empty((aperture, aperture), dtype=pt_float)
        MtR = numpy.empty((aperture,), dtype=pt_float)
        offset = aperture // 2
        for j in range(aperture):
            MtR[j] = numpy.real(W2R[j - offset])
            for i in range(aperture):
                MtM[j, i] = numpy.real(W2[i - j])
        # solve using Cholesky decomposition
        L = numpy.linalg.cholesky(MtM)
        coefs = numpy.linalg.solve(numpy.transpose(L.conjugate()),
                                   numpy.linalg.solve(L, MtR)).astype(pt_float)
        # send filter output
        fil_frame = Frame()
        if self.config['direction'] == 'horizontal':
            fil_frame.data = coefs.reshape((1, -1, 1))
        else:
            fil_frame.data = coefs.reshape((-1, 1, 1))
        fil_frame.type = 'fil'
        audit = fil_frame.metadata.get('audit')
        audit += 'data = FilterCoefficients()\n'
        audit += '    frequency: {}\n'.format(self.config['frequency'])
        audit += '    gain: {}\n'.format(self.config['gain'])
        if self.config['weight']:
            audit += '    weight: {}\n'.format(self.config['weight'])
        audit += '    aperture: {}\n'.format(aperture)
        audit += '    interp: {}\n'.format(self.config['interp'])
        audit += '    direction: {}\n'.format(self.config['direction'])
        fil_frame.metadata.set('audit', audit)
        self.send('filter', fil_frame)
        # compute actual response
        padded = numpy.zeros(pad_len * 2)
        for j in range(aperture):
            padded[j - offset] = coefs[j]
        response = numpy.fft.rfft(padded)
        # send response output
        resp_frame = Frame()
        resp_frame.type = 'resp'
        if self.config['weight']:
            resp_frame.data = numpy.stack(
                (int_freq, int_gain, int_wgt_copy, numpy.real(response)))
            labels = 'normalised frequency', 'ideal gain', 'weight', 'actual gain'
        else:
            resp_frame.data = numpy.stack(
                (int_freq, int_gain, numpy.real(response)))
            labels = 'normalised frequency', 'ideal gain', 'actual gain'
        resp_frame.metadata.set('labels', repr(labels))
        audit = resp_frame.metadata.get('audit')
        audit += 'data = FilterResponse()\n'
        audit += '    frequency: {}\n'.format(self.config['frequency'])
        audit += '    gain: {}\n'.format(self.config['gain'])
        if self.config['weight']:
            audit += '    weight: {}\n'.format(self.config['weight'])
        audit += '    aperture: {}\n'.format(aperture)
        audit += '    interp: {}\n'.format(self.config['interp'])
        audit += '    direction: {}\n'.format(self.config['direction'])
        resp_frame.metadata.set('audit', audit)
        self.send('response', resp_frame)
