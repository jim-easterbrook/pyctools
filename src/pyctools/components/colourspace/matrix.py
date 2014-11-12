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

"""Apply a user supplied colour matrix.

Converts ``n``-component input to ``m``-component output with a
user-supplied ``m x n`` matrix.

The :py:meth:`~Matrix.matrix` method is used to update the matrix. No
processing happens until a matrix is received, and a new matrix can be
applied while the component is running.

The matrix is supplied as a :py:class:`~pyctools.core.frame.Frame`
object, allowing an audit trail to be included describing it. The
matrix data can be either one ``m x n``
:py:class:`numpy:numpy.ndarray` or ``m`` ``1 x n``
:py:class:`numpy:numpy.ndarray` objects. In the former case the output
data will be a single "dstacked" image, in the latter it will be a
list of single component images.

"""

__all__ = ['Matrix']
__docformat__ = 'restructuredtext en'

from guild.actor import *
import numpy

from pyctools.core.base import Transformer

class Matrix(Transformer):
    inputs = ['input', 'matrix']

    def initialise(self):
        self.set_ready(False)

    @actor_method
    def matrix(self, new_matrix):
        """matrix(new_matrix)

        Matrix data input.

        :param Frame new_matrix: A :py:class:`~pyctools.core.frame.Frame`
            containing the matrix data.

        """
        for matrix in new_matrix.data:
            if not isinstance(matrix, numpy.ndarray):
                self.logger.warning('Each matrix input must be a numpy array')
                return
            if matrix.ndim != 2:
                self.logger.warning('Each matrix input must be 2 dimensional')
                return
        self.matrix_coefs = new_matrix
        self.set_ready(True)

    def transform(self, in_frame, out_frame):
        data_in = in_frame.as_numpy(dtype=numpy.float32, dstack=True)[0]
        out_frame.data = []
        for matrix in self.matrix_coefs.data:
            if data_in.shape[2] != matrix.shape[1]:
                self.logger.critical(
                    'Input has %d components, matrix expects %d',
                    data_in.shape[2], matrix.shape[1])
                return False
            out_frame.data.append(numpy.dot(data_in, matrix.T))
        audit = out_frame.metadata.get('audit')
        audit += 'data = Matrix(data)\n'
        audit += '    matrix: {\n%s}\n' % (
            self.matrix_coefs.metadata.get('audit'))
        out_frame.metadata.set('audit', audit)
        return True
