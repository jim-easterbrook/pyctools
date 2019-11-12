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

__all__ = ['ErrorFeedbackQuantise']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.base import Transformer

class ErrorFeedbackQuantise(Transformer):
    """Quantisation with error feedback.

    Round data to integer values, using error feedback (see
    http://www.bbc.co.uk/rd/publications/rdreport_1987_12) to reduce the
    visibility of quantisation effects.

    Note that if the input image is already quantised this component
    will have no effect. Hence it is recommended always to be used
    before any component that truncates the data, such as
    :py:class:`~pyctools.components.io.imagefilepil.ImageFileWriterPIL`.

    """

    def transform(self, in_frame, out_frame):
        self.update_config()
        # get data
        data = in_frame.as_numpy(copy=True)
        h, w, c = data.shape
        if data.dtype == numpy.uint8:
            pass
        elif w >= h:
            # seed error feedback with random numbers in range [0, 1)
            # mean value 0.5 means numpy.floor is effectively 'round'
            residue = numpy.random.random((h, c)).astype(data.dtype)
            for x in range(w):
                # add residue
                c_data = data[::, x, ::] + residue
                # quantise
                q_data = numpy.floor(c_data)
                data[::, x, ::] = q_data
                # compute new residue
                residue = c_data - q_data
        else:
            # seed error feedback with random numbers in range [0, 1)
            # mean value 0.5 means numpy.floor is effectively 'round'
            residue = numpy.random.random((w, c)).astype(data.dtype)
            for y in range(h):
                # add residue
                c_data = data[y, ::, ::] + residue
                # quantise
                q_data = numpy.floor(c_data)
                data[y, ::, ::] = q_data
                # compute new residue
                residue = c_data - q_data
        out_frame.data = data
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = ErrorFeedbackQuantise(data)\n'
        out_frame.metadata.set('audit', audit)
        return True
