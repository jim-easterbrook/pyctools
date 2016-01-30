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

__all__ = ['ImageFileReaderCV', 'ImageFileWriterCV']
__docformat__ = 'restructuredtext en'

import time

import cv2
import numpy

from pyctools.core.config import ConfigBool, ConfigPath, ConfigStr
from pyctools.core.base import Component, Transformer
from pyctools.core.frame import Frame, Metadata

class ImageFileReaderCV(Component):
    """Read a still image file using OpenCV library.

    The file is read with minimum changes to the data, so a 16-bit depth
    file will result in a floating point image with data in the usual
    0..255 range.

    If you have a file format that OpenCV doesn't recognise, try the
    :py:class:`~pyctools.components.io.imagefilepil.ImageFileReaderPIL`
    component instead.

    ========  ===  ====
    Config
    ========  ===  ====
    ``path``  str  Path name of file to be read.
    ========  ===  ====

    """
    inputs = []
    with_outframe_pool = False

    def initialise(self):
        self.config['path'] = ConfigPath()

    def on_start(self):
        # read file
        self.update_config()
        path = self.config['path']
        out_frame = Frame()
        image = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        # scale data
        if image.dtype == numpy.uint8:
            pass
        elif image.dtype == numpy.uint16:
            image = image.astype(numpy.float32) / numpy.float32(2 ** 8)
        else:
            self.logger.error('Cannot handle %s data type', str(image.dtype))
            self.stop()
            return
        # rearrange components
        if image.shape[2] == 4:
            # RGBA image
            B = image[:, :, 0]
            G = image[:, :, 1]
            R = image[:, :, 2]
            A = image[:, :, 3]
            image = numpy.dstack((R, G, B, A))
            out_frame.type = 'RGBA'
        elif image.shape[2] == 3:
            # RGB image
            B = image[:, :, 0]
            G = image[:, :, 1]
            R = image[:, :, 2]
            image = numpy.dstack((R, G, B))
            out_frame.type = 'RGB'
        elif image.shape[2] == 1:
            out_frame.type = 'Y'
        else:
            out_frame.type = '???'
        # send output frame
        out_frame.data = image
        out_frame.frame_no = 0
        out_frame.metadata.from_file(path)
        audit = out_frame.metadata.get('audit')
        audit += 'data = {}\n'.format(path)
        out_frame.metadata.set('audit', audit)
        self.send('output', out_frame)
        # shut down pipeline
        self.stop()


class ImageFileWriterCV(Transformer):
    """Write a still image file using OpenCV library.

    See the `OpenCV documentation
    <http://docs.opencv.org/2.4.11/modules/highgui/doc/reading_and_writing_images_and_video.html#imwrite>`_
    for more detail on the possible parameters.

    If you need to write a file format that OpenCV can't do, try the
    :py:class:`~pyctools.components.io.imagefilepil.ImageFileWriterPIL`
    component instead.

    ============  ====  ====
    Config
    ============  ====  ====
    ``path``      str   Path name of file to be written.
    ``16bit``     bool  Write a 16-bit depth file, if the format supports it.
    ``JPEG_xxx``  int   OpenCV IMWRITE_JPEG_xxx parameter.
    ``PNG_xxx``   int   OpenCV IMWRITE_PNG_xxx parameter.
    ============  ====  ====

    """
    def initialise(self):
        self.done = False
        self.config['path'] = ConfigPath(exists=False)
        self.config['16bit'] = ConfigBool()
        self.cv2_params = [
            x[8:] for x in cv2.__dict__ if x.startswith('IMWRITE_')]
        self.cv2_params.sort()
        for item in self.cv2_params:
            self.config[item] = ConfigStr()

    def transform(self, in_frame, out_frame):
        if self.done:
            return True
        self.update_config()
        path = self.config['path']
        params = []
        for item in self.cv2_params:
            if self.config[item]:
                params.append(getattr(cv2, 'IMWRITE_' + item))
                params.append(int(self.config[item]))
        # convert data
        if self.config['16bit']:
            image = in_frame.as_numpy() * numpy.float32(2 ** 8)
            image = image.astype(numpy.uint16)
        else:
            image = in_frame.as_numpy(dtype=numpy.uint8)
        # rearrange components
        if image.shape[2] == 4:
            # RGBA image
            R = image[:, :, 0]
            G = image[:, :, 1]
            B = image[:, :, 2]
            A = image[:, :, 3]
            image = numpy.dstack((B, G, R, A))
        elif image.shape[2] == 3:
            # RGB image
            R = image[:, :, 0]
            G = image[:, :, 1]
            B = image[:, :, 2]
            image = numpy.dstack((B, G, R))
        # save image
        cv2.imwrite(path, image, params)
        # save metadata
        md = Metadata().copy(in_frame.metadata)
        audit = md.get('audit')
        audit += '{} = data\n'.format(path)
        for item in self.cv2_params:
            if self.config[item]:
                audit += '    {}: {}\n'.format(item, int(self.config[item]))
        md.set('audit', audit)
        md.to_file(path)
        self.done = True
        return True
