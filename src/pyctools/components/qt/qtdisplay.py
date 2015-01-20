#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-15  Jim Easterbrook  jim@jim-easterbrook.me.uk
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

"""Display images in a Qt window.

This is a "pass through" component that can be inserted anywhere in a
pipeline to display the images at that point.

The displayed image can be enlarged or reduced in size by setting the
``expand`` and ``shrink`` config values. The size changing is done
within Qt.

The ``framerate`` config item sets a target rate (default value 25
fps). If the incoming video cannot keep up then frames will be
repeated. Otherwise the entire processing pipeline is slowed down to
supply images at the correct rate.

=============  ===  ====
Config
=============  ===  ====
``expand``     int  Image up-conversion factor.
``shrink``     int  Image down-conversion factor.
``framerate``  int  Target frame rate.
``stats``      str  Show actual frame rate statistics. Can be ``'off'`` or ``'on'``.
=============  ===  ====

"""

__all__ = ['QtDisplay']
__docformat__ = 'restructuredtext en'

from collections import deque
import logging
import sys

import numpy
from OpenGL import GL
from PyQt4 import QtGui, QtCore, QtOpenGL
from PyQt4.QtCore import Qt

from pyctools.core.config import ConfigInt, ConfigEnum
from pyctools.core.base import Transformer

class SimpleDisplay(QtOpenGL.QGLWidget):
    def __init__(self, parent=None, flags=0):
        super(SimpleDisplay, self).__init__(parent, None, flags)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.in_queue = deque()
        self.framerate = 25
        self.frame_count = 0
        self.missed_count = 0
        self.image = None
        # create timer to show frames at regular intervals
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.timer_show_frame)

    def start(self):
        # start timer
        self.timer.start(1000 // self.framerate)

    def show_frame(self, frame, image, scale, framerate, stats):
        # this method will be called from another thread, so do
        # nothing except put stuff on queue
        self.in_queue.append((frame, image, scale, framerate, stats))

    def timer_show_frame(self):
        if not self.in_queue:
            self.missed_count += 1
            return
        frame, image, scale, framerate, stats = self.in_queue.popleft()
        if framerate != self.framerate:
            self.framerate = framerate
            self.timer.setInterval(1000 // self.framerate)
        self.image = image
        h, w = frame.size()
        self.resize(w * scale, h * scale)
        if not self.isVisible():
            self.show()
        self.updateGL()
        self.frame_count += 1
        if self.frame_count >= 200:
            if stats:
                miss_rate = 100.0 * float(self.missed_count) / float(
                    self.missed_count + self.frame_count)
                self.logger.warning(
                    'Showing %.1f%% of target frame rate', 100.0 - miss_rate)
            self.frame_count = 0
            self.missed_count = 0

    def shut_down(self):
        self.timer.stop()
        self.close()

    def initializeGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_TEXTURE_2D)
        texture = GL.glGenTextures(1)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glTexParameterf(
            GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameterf(
            GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)

    def resizeGL(self, w, h):
        GL.glViewport(0, 0, w, h)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(0, 1, 0, 1, -1, 1)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

    def paintGL(self):
        if self.image is None:
            return
        ylen, xlen, bpc = self.image.shape
        if bpc == 3:
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB, xlen, ylen,
                            0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, self.image)
        elif bpc == 1:
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB, xlen, ylen,
                            0, GL.GL_LUMINANCE, GL.GL_UNSIGNED_BYTE, self.image)
        GL.glBegin(GL.GL_QUADS)
        GL.glTexCoord2i(0, 0)
        GL.glVertex2i(0, 1)
        GL.glTexCoord2i(0, 1)
        GL.glVertex2i(0, 0)
        GL.glTexCoord2i(1, 1)
        GL.glVertex2i(1, 0)
        GL.glTexCoord2i(1, 0)
        GL.glVertex2i(1, 1)
        GL.glEnd()
        GL.glFlush()

class QtDisplay(Transformer):
    def initialise(self):
        self.config['shrink'] = ConfigInt(min_value=1, dynamic=True)
        self.config['expand'] = ConfigInt(min_value=1, dynamic=True)
        self.config['framerate'] = ConfigInt(min_value=1, value=25)
        self.config['stats'] = ConfigEnum(('off', 'on'))
        self.last_frame_type = None
        self.display = SimpleDisplay(None, Qt.Window | Qt.WindowStaysOnTopHint)

    def process_start(self):
        super(QtDisplay, self).process_start()
        self.display.start()

    def transform(self, in_frame, out_frame):
        self.update_config()
        shrink = self.config['shrink']
        expand = self.config['expand']
        framerate = self.config['framerate']
        stats = self.config['stats'] == 'on'
        numpy_image = in_frame.as_numpy(dtype=numpy.uint8)
        if not numpy_image.flags.contiguous:
            numpy_image = numpy.ascontiguousarray(numpy_image)
        ylen, xlen, bpc = numpy_image.shape
        if bpc == 3:
            if in_frame.type != 'RGB' and in_frame.type != self.last_frame_type:
                self.logger.warning('Expected RGB input, got %s', in_frame.type)
        elif bpc == 1:
            if in_frame.type != 'Y' and in_frame.type != self.last_frame_type:
                self.logger.warning('Expected Y input, got %s', in_frame.type)
        else:
            self.logger.critical(
                'Cannot display %s frame with %d components', in_frame.type, bpc)
            return False
        self.last_frame_type = in_frame.type
        scale = float(expand) / float(shrink)
        self.display.show_frame(in_frame, numpy_image, scale, framerate, stats)
        return True

    def onStop(self):
        super(QtDisplay, self).onStop()
        self.display.shut_down()

def main():
    import logging
    from ..io.rawfilereader import RawFileReader
    from ..colourspace.yuvtorgb import YUVtoRGB
    from guild.actor import pipeline, start, stop, wait_for

    if len(sys.argv) != 2:
        print('usage: %s yuv_video_file' % sys.argv[0])
        return 1
    logging.basicConfig(level=logging.DEBUG)
    print('Qt display demonstration')
    QtGui.QApplication.setAttribute(Qt.AA_X11InitThreads)
    app = QtGui.QApplication([])
    source = RawFileReader()
    config = source.get_config()
    config['path'] = sys.argv[1]
    config['looping'] = 'reverse'
    source.set_config(config)
    conv = YUVtoRGB()
    sink = QtDisplay()
    pipeline(source, conv, sink)
    start(source, conv, sink)
    try:
        app.exec_()
    finally:
        stop(source, conv, sink)
        wait_for(source, conv, sink)
    return 0

if __name__ == '__main__':
    sys.exit(main())
