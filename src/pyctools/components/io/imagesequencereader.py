#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2019-20  Pyctools contributors
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

__all__ = ['ImageSequenceReader']
__docformat__ = 'restructuredtext en'

import os

try:
    import cv2
except ImportError:
    cv2 = None
import numpy
try:
    import PIL.Image as PIL
except ImportError:
    PIL = None

from pyctools.core.config import ConfigEnum, ConfigPath
from pyctools.core.base import Component
from pyctools.core.frame import Metadata
from pyctools.core.types import pt_float


class ImageSequenceReader(Component):
    """Read a set of image files (JPEG, PNG, TIFF, etc).

    The ``firstfile`` and ``lastfile`` strings must be identical apart
    from a decimal number that signifies the position in the sequence.
    This number can be anywhere in the filename and need not have
    leading zeros.

    =============  ====  ====
    Config
    =============  ====  ====
    ``firstfile``  str   Path name of first file in the sequence.
    ``lastfile``   str   Path name of last file in the sequence.
    ``looping``    str   Whether to play continuously. Can be ``'off'`` or ``'repeat'``.
    =============  ====  ====

    """

    inputs = []

    def initialise(self):
        self.metadata = None
        self.config['firstfile'] = ConfigPath()
        self.config['lastfile'] = ConfigPath()
        self.config['looping'] = ConfigEnum(choices=('off', 'repeat'))

    def process_frame(self):
        self.update_config()
        if self.metadata is None:
            first_name = self.config['firstfile']
            last_name = self.config['lastfile']
            # read metadata
            self.metadata = Metadata().from_file(first_name)
            self.metadata.set_audit(
                self, 'data = {}..{}\n'.format(
                    os.path.basename(first_name), os.path.basename(last_name)),
                with_config=self.config)
            # compare file names
            prefix = ''
            for a, b in zip(first_name, last_name):
                if a != b:
                    break
                prefix += a
            suffix = ''
            for a, b in zip(first_name[::-1], last_name[::-1]):
                if a != b:
                    break
                suffix = a + suffix
            first_frame = first_name[len(prefix):-len(suffix)]
            last_frame = last_name[len(prefix):-len(suffix)]
            self.format_ = prefix + '{:0' + str(len(first_frame)) + 'd}' + suffix
            self.first_frame = int(first_frame)
            self.last_frame = int(last_frame)
            # initialise looping parameters
            self.frame_no = 0
            self.frame_idx = self.first_frame
        # get path of this frame
        if self.frame_idx > self.last_frame:
            if self.config['looping'] == 'off':
                raise StopIteration()
            self.frame_idx = self.first_frame
        path = self.format_.format(self.frame_idx)
        self.frame_idx += 1
        # read data
        image = None
        if cv2:
            # try OpenCV first, as it can do 16 bit
            image = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            # scale data
            if image.dtype == numpy.uint8:
                pass
            elif image.dtype == numpy.uint16:
                image = image.astype(numpy.float32) / numpy.float32(2 ** 8)
            else:
                self.logger.error('Cannot handle %s data type', str(image.dtype))
                raise StopIteration()
            # rearrange components
            if image.shape[2] == 4:
                # RGBA image
                B, G, R, A = numpy.dsplit(image, 4)
                image = numpy.dstack((R, G, B, A))
                frame_type = 'RGBA'
            elif image.shape[2] == 3:
                # RGB image
                B, G, R = numpy.dsplit(image, 3)
                image = numpy.dstack((R, G, B))
                frame_type = 'RGB'
            elif image.shape[2] == 1:
                frame_type = 'Y'
            else:
                frame_type = '???'
        if PIL and image is None:
            # try PIL as it handles more image types
            image = PIL.open(path)
            image.load()
            frame_type = image.mode
        if image is None:
            self.logger.error('Cannot read file %s', path)
            raise StopIteration()
        # send frame
        out_frame = self.outframe_pool['output'].get()
        out_frame.data = image
        out_frame.type = frame_type
        out_frame.frame_no = self.frame_no
        self.frame_no += 1
        out_frame.metadata.copy(self.metadata)
        self.send('output', out_frame)
