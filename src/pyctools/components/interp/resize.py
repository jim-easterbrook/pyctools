#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-19  Pyctools contributors
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

__all__ = ['Resize', 'FilterResponse']
__docformat__ = 'restructuredtext en'

import sys
if 'sphinx' in sys.modules:
    __all__.append('resize_frame')

import numpy

from pyctools.core.config import ConfigInt
from pyctools.core.base import Transformer
from .resizecore import resize_frame

class Resize(Transformer):
    """Filter an image and/or resize with interpolation.

    Resize (or just filter) an image using user supplied filter(s). The
    filters are supplied in a :py:class:`~pyctools.core.frame.Frame`
    object sent to the :py:meth:`filter` input. If the frame data's 3rd
    dimension is unity then the same filter is applied to each component
    of the input. Alternatively the frame data's 3rd dimension should
    match the input's, allowing a different filter to be applied to each
    colour.

    Images can be resized by almost any amount. The resizing is
    controlled by integer "up" and "down" factors and is not constrained
    to simple ratios such as 2:1 or 5:4.

    To filter images without resizing leave the "up" and "down" factors
    at their default value of 1.

    The core method :py:meth:`resize_frame` is written in Cython,
    allowing real-time image resizing on a typical computer.

    The ``filter`` output forwards the filter frame whenever it changes.
    It can be connected to a :py:class:`FilterResponse` component to
    compute the (new) frequency response.

    Config:

    =========  ===  ====
    ``xup``    int  Horizontal up-conversion factor.
    ``xdown``  int  Horizontal down-conversion factor.
    ``yup``    int  Vertical up-conversion factor.
    ``ydown``  int  Vertical down-conversion factor.
    =========  ===  ====

    """
    inputs = ['input', 'filter']    #:
    outputs = ['output', 'filter']  #:

    def initialise(self):
        self.config['xup'] = ConfigInt(min_value=1)
        self.config['xdown'] = ConfigInt(min_value=1)
        self.config['yup'] = ConfigInt(min_value=1)
        self.config['ydown'] = ConfigInt(min_value=1)
        self.filter_frame = None

    def get_filter(self):
        new_filter = self.input_buffer['filter'].peek()
        if not new_filter:
            return False
        if new_filter == self.filter_frame:
            return True
        self.send('filter', new_filter)
        filter_coefs = new_filter.as_numpy(dtype=numpy.float32)
        if filter_coefs.ndim != 3:
            self.logger.warning('Filter input must be 3 dimensional')
            return False
        ylen, xlen = filter_coefs.shape[:2]
        if (xlen % 2) != 1 or (ylen % 2) != 1:
            self.logger.warning('Filter input must have odd width & height')
            return False
        self.filter_frame = new_filter
        self.filter_coefs = filter_coefs
        self.fil_count = None
        return True

    def transform(self, in_frame, out_frame):
        if not self.get_filter():
            return False
        self.update_config()
        x_up = self.config['xup']
        x_down = self.config['xdown']
        y_up = self.config['yup']
        y_down = self.config['ydown']
        in_data = in_frame.as_numpy(dtype=numpy.float32)
        if self.fil_count != self.filter_coefs.shape[2]:
            self.fil_count = self.filter_coefs.shape[2]
            if self.fil_count != 1 and self.fil_count != in_data.shape[2]:
                self.logger.warning('Mismatch between %d filters and %d images',
                                    self.fil_count, in_data.shape[2])
        norm_filter = self.filter_coefs * numpy.float32(x_up * y_up)
        out_frame.data = resize_frame(
            in_data, norm_filter, x_up, x_down, y_up, y_down)
        audit = out_frame.metadata.get('audit')
        audit += 'data = Resize(data)\n'
        if x_up != 1 or x_down != 1:
            audit += '    x_up: %d, x_down: %d\n' % (x_up, x_down)
        if y_up != 1 or y_down != 1:
            audit += '    y_up: %d, y_down: %d\n' % (y_up, y_down)
        audit += '    filter: {\n'
        for line in self.filter_frame.metadata.get('audit').splitlines():
            audit += '        ' + line + '\n'
        audit += '        }\n'
        out_frame.metadata.set('audit', audit)
        return True


class FilterResponse(Transformer):
    """Compute frequency response of a 1-D filter.

    The filter is padded to a power of 2 (e.g. 1024) before computing
    the Fourier transform. The magnitude of the positive frequency half
    is output in a form suitable for the
    :py:class:`~pyctools.components.io.plotdata.PlotData` component.

    """
    inputs = ['filter']     #:
    outputs = ['response']  #:

    def transform(self, in_frame, out_frame):
        filter_coefs = in_frame.as_numpy(dtype=numpy.float32)
        if filter_coefs.ndim != 3:
            self.logger.warning('Filter frame must be 3 dimensional')
            return False
        ylen, xlen, comps = filter_coefs.shape
        if xlen > 1 and ylen > 1:
            return False
        responses = []
        pad_len = 1024
        if xlen > 1:
            while pad_len < xlen:
                pad_len *= 2
            padded = numpy.zeros(pad_len)
            for c in range(comps):
                padded[0:xlen] = filter_coefs[0, :, c]
                responses.append(numpy.absolute(numpy.fft.rfft(padded)))
        elif ylen > 1:
            while pad_len < ylen:
                pad_len *= 2
            padded = numpy.zeros(pad_len)
            for c in range(comps):
                padded[0:ylen] = filter_coefs[:, 0, c]
                responses.append(numpy.absolute(numpy.fft.rfft(padded)))
        responses.insert(0, numpy.linspace(0.0, 0.5, responses[0].shape[0]))
        # generate output frame
        out_frame.data = numpy.stack(responses)
        out_frame.type = 'resp'
        labels = ['normalised frequency']
        if comps > 1:
            for c in range(comps):
                labels.append('component {}'.format(c))
        out_frame.metadata.set('labels', repr(labels))
        audit = out_frame.metadata.get('audit')
        audit += 'data = FilterResponse(data)\n'
        out_frame.metadata.set('audit', audit)
        return True
