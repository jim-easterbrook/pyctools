#!/usr/bin/env python
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

__all__ = ['Matrix']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.base import Transformer

class Matrix(Transformer):
    """Apply a user supplied colour matrix.

    Converts ``n``-component input to ``m``-component output with a
    user-supplied ``m x n`` matrix.

    The ``matrix`` input is used to update the matrix. No processing
    happens until a matrix is received, and a new matrix can be applied
    while the component is running.

    The matrix is supplied as a :py:class:`~pyctools.core.frame.Frame`
    object, allowing an audit trail to be included describing it. The
    frame's data must be an ``m x n`` :py:class:`numpy:numpy.ndarray`
    object. The frame's frame number must be less than zero.

    """

    inputs = ['input', 'matrix']    #:

    def initialise(self):
        self.matrix_frame = None

    def get_matrix(self):
        new_matrix = self.input_buffer['matrix'].peek()
        if new_matrix == self.matrix_frame:
            return True
        matrix = new_matrix.as_numpy()
        if matrix.ndim != 2:
            self.logger.error('Matrix input must be 2 dimensional')
            return False
        self.matrix_frame = new_matrix
        self.matrix_coefs = matrix
        return True

    def transform(self, in_frame, out_frame):
        if not self.get_matrix():
            return False
        data_in = in_frame.as_numpy()
        out_frame.data = numpy.dot(data_in, self.matrix_coefs.T)
        audit = out_frame.metadata.get('audit')
        audit += 'data = Matrix(data)\n'
        audit += '    matrix: {\n'
        for line in self.matrix_frame.metadata.get('audit').splitlines():
            audit += '        ' + line + '\n'
        audit += '        }\n'
        out_frame.metadata.set('audit', audit)
        return True
