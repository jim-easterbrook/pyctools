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

"""Pyctools "Frame" class.

This is a fairly free-form container, but every Frame object must have:

* a frame number
* a list of zero or more data items, which may themselves be Frames
* a type description string, such as "RGB"
* a Metadata item

"""

__all__ = ['Frame']

import numpy
import PIL.Image

from .metadata import Metadata

class Frame(object):
    def __init__(self):
        self.frame_no = -1
        self.data = []
        self.type = 'empty'
        self.metadata = Metadata()

    def initialise(self, other):
        self.frame_no = other.frame_no
        self.data = other.data
        self.type = other.type
        self.metadata.copy(other.metadata)

    def as_numpy(self, dtype=None, dstack=None):
        result = []
        for data in self.data:
            if isinstance(data, numpy.ndarray):
                new_data = data
            elif isinstance(data, PIL.Image):
                if data.mode == 'F':
                    new_data = numpy.array(data, dtype=numpy.float32)
                elif data.mode == 'I':
                    new_data = numpy.array(data, dtype=numpy.int32)
                elif dtype is not None:
                    new_data = numpy.array(data, dtype=dtype)
                else:
                    new_data = numpy.array(data, dtype=numpy.float32)
            else:
                raise RuntimeError(
                    'Cannot convert "%s" to numpy' % data.__class__.__name__)
            if dtype is not None and new_data.dtype != dtype:
                if dtype == numpy.uint8:
                    new_data = new_data.clip(0, 255)
                elif dtype == numpy.uint16:
                    new_data = new_data.clip(0, 2**16 - 1)
                new_data = new_data.astype(dtype)
            result.append(new_data)
        if dstack is None:
            pass
        elif dstack:
            if len(result) > 1 or result[0].ndim < 3:
                result = [numpy.dstack(result)]
        else:
            if result[0].ndim > 2:
                new_result = []
                for data in result:
                    for c in range(data.shape[2]):
                        new_result.append(data[:,:,c])
                result = new_result
        return result

    def as_PIL(self):
        result = []
        for data in self.data:
            if isinstance(data, numpy.ndarray):
                if data.dtype == numpy.uint8:
                    result.append(PIL.Image.fromarray(data))
                else:
                    result.append(PIL.Image.fromarray(
                        data.clip(0, 255).astype(numpy.uint8)))
            elif isinstance(data, PIL.Image):
                result.append(data)
            else:
                raise RuntimeError(
                    'Cannot convert "%s" to PIL' % data.__class__.__name__)
        return result
