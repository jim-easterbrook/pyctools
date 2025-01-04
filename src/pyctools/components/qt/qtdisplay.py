#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-25  Pyctools contributors
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

__all__ = ['QtDisplay']
__docformat__ = 'restructuredtext en'

from collections import deque
import sys
import time

import numpy
if 'sphinx' in sys.modules:
    GL = None
else:
    from OpenGL import GL

from pyctools.core.config import ConfigBool, ConfigInt, ConfigStr
from pyctools.core.base import Transformer
from pyctools.core.qt import (LowEventPriority, qt_version_info, qt_package,
                              QtCore, QtEventLoop, QtGui, QtSlot, QtWidgets)

if qt_package == 'PyQt6':
    from PyQt6.QtOpenGLWidgets import QOpenGLWidget
elif qt_package == 'PySide6':
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
else:
    QOpenGLWidget = QtWidgets.QOpenGLWidget

if qt_version_info < (5, 4):
    raise ImportError('Qt version 5.4 or higher required')


class GLDisplay(QOpenGLWidget):
    def __init__(self, logger, *arg, **kwds):
        super(GLDisplay, self).__init__(*arg, **kwds)
        self.logger = logger
        self.in_queue = deque()
        self.black_image = numpy.zeros((1, 1, 1), dtype=numpy.uint8)
        self.show_black = True
        self.paused = False
        self._display_period = 0.0
        self._frame_count = -10
        self.frame_period = 1.0 / 25.0
        self._clock_history = deque(maxlen=100)
        self.frameSwapped.connect(self.frame_swapped)

    @QtSlot(float)
    def done_swap(self, now):
        # called by rendering thread after each buffer swap
        if self._frame_count < 0:
            # initialising
            self._frame_count += 1
            if self._clock_history:
                self._display_period = now - self._clock_history[0]
                self._next_frame_due = now + self._display_period
                self._block_start = self._next_frame_due
            self._clock_history.clear()
            self._clock_history.append(now)
            self.show_black = True
            return
        self._clock_history.append(now)
        # compute frame period
        period = ((now - self._clock_history[0]) /
                  float(len(self._clock_history) - 1))
        self._display_period += (period - self._display_period) / float(
            len(self._clock_history) - 1)
        # clock is earliest of now and extrapolated times
        display_clock = min(
            now, self._clock_history[-2] + self._display_period)
        if len(self._clock_history) >= 3:
            display_clock = min(
                display_clock,
                self._clock_history[-3] + (self._display_period * 2))
        # adjust frame clock
        while self._next_frame_due < display_clock:
            self._next_frame_due += self.frame_period
            if not (self.paused or self.sync or len(self.in_queue) <= 1):
                # drop a frame to keep up
                self.in_queue.popleft()
                self._frame_count += 1
        if self.paused:
            self.show_black = False
        elif (self.in_queue and
              self._next_frame_due <= display_clock + self._display_period):
            if self.sync:
                # lock frame clock to display clock
                error = (display_clock + (self._display_period / 2.0) -
                         self._next_frame_due)
                if abs(error) < self._display_period * 0.25:
                    self._next_frame_due += error / 8.0
            # show frame immmediately
            self.next_frame()
            self.show_black = False
        elif not self.repeat:
            # show blank frame immediately
            self.show_black = True

    def next_frame(self):
        in_frame, self.numpy_image = self.in_queue.popleft()
        self._next_frame_due += self.frame_period
        self._frame_count += 1
        if self._frame_count <= 0:
            self._block_start = self._next_frame_due
        if self._next_frame_due - self._block_start > 5.0:
            if self.show_stats:
                frame_rate = float(self._frame_count) / (
                    self._next_frame_due - self._block_start)
                self.logger.warning(
                    'Average frame rate: %.2fHz', frame_rate)
            self._frame_count = 0
            self._block_start = self._next_frame_due

    def step(self):
        if self.in_queue:
            self.next_frame()
            self.show_black = False

    def initializeGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_TEXTURE_2D)
        texture = GL.glGenTextures(1)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glDisable(GL.GL_TEXTURE_2D)

    def resizeGL(self, w, h):
        GL.glViewport(0, 0, w, h)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(0, 1, 0, 1, -1, 1)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

    def paintGL(self):
        if self.show_black:
            image = self.black_image
        else:
            image = self.numpy_image
        ylen, xlen, bpc = image.shape
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glTexParameterf(
            GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameterf(
            GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        if bpc == 3:
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB, xlen, ylen,
                            0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, image)
        elif bpc == 1:
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB, xlen, ylen,
                            0, GL.GL_LUMINANCE, GL.GL_UNSIGNED_BYTE, image)
        else:
            return
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
        GL.glDisable(GL.GL_TEXTURE_2D)

    def startup(self):
        pass

    def shutdown(self):
        pass

    @QtSlot()
    def frame_swapped(self):
        now = time.time()
        self.done_swap(now)
        # schedule next frame
        self.update()


class QtDisplay(Transformer, QtWidgets.QWidget):
    """Display images in a Qt window.

    This is a "pass through" component that can be inserted anywhere in
    a pipeline to display the images at that point.

    The displayed image can be enlarged or reduced in size by setting
    the ``expand`` and ``shrink`` config values. The size changing is
    done within OpenGL.

    The ``framerate`` config item sets a target rate (default value 25
    fps). If the incoming video cannot keep up then frames will be
    repeated. Otherwise the entire processing pipeline is slowed down to
    supply images at the correct rate.

    =============  ====  ====
    Config
    =============  ====  ====
    ``title``      str   Window title.
    ``expand``     int   Image up-conversion factor.
    ``shrink``     int   Image down-conversion factor.
    ``framerate``  int   Target frame rate.
    ``repeat``     bool  Repeat frames until next one arrives.
    ``sync``       bool  Synchronise to video card frame rate.
    ``stats``      bool  Show actual frame rate statistics.
    =============  ====  ====

    """

    event_loop = QtEventLoop

    def __init__(self, **config):
        super(QtDisplay, self).__init__(**config)
        self.setWindowFlags(QtCore.Qt.WindowType.Window |
                            QtCore.Qt.WindowType.WindowStaysOnTopHint)
        dpr = self.window().devicePixelRatio()
        if int(dpr) != dpr:
            self.logger.warning('Non-integer screen pixel ratio %g', dpr)
        self.setLayout(QtWidgets.QGridLayout())
        fmt = QtGui.QSurfaceFormat()
        fmt.setProfile(
            QtGui.QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
        fmt.setSwapBehavior(QtGui.QSurfaceFormat.SwapBehavior.DoubleBuffer)
        fmt.setSwapInterval(1)
        self.display = GLDisplay(self.logger)
        self.display.setFormat(fmt)
        self.layout().addWidget(self.display, 0, 0, 1, 4)
        # control buttons
        self.pause_button = QtWidgets.QPushButton('pause')
        self.pause_button.setShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key.Key_Space))
        self.pause_button.clicked.connect(self.pause)
        self.layout().addWidget(self.pause_button, 1, 0)
        self.step_button = QtWidgets.QPushButton('step')
        self.step_button.setShortcut(
            QtGui.QKeySequence.StandardKey.MoveToNextChar)
        self.step_button.clicked.connect(self.step)
        self.layout().addWidget(self.step_button, 1, 1)
        self.display_size = None
        self.last_frame_type = None

    def initialise(self):
        self.config['title'] = ConfigStr()
        self.config['shrink'] = ConfigInt(min_value=1)
        self.config['expand'] = ConfigInt(min_value=1)
        self.config['framerate'] = ConfigInt(min_value=1, value=25)
        self.config['sync'] = ConfigBool(value=True)
        self.config['repeat'] = ConfigBool(value=True)
        self.config['stats'] = ConfigBool()

    def pause(self):
        self.display.paused = not self.display.paused
        if self.display.paused:
            self.pause_button.setText('play')
        else:
            self.pause_button.setText('pause')

    def step(self):
        if not self.display.paused:
            self.pause()
            return
        self.display.step()

    def closeEvent(self, event):
        event.accept()
        self.stop()

    def on_start(self):
        self.on_set_config()
        self.display.startup()

    def on_stop(self):
        self.display.shutdown()
        self.close()

    def on_set_config(self):
        self.update_config()
        self.setWindowTitle(self.config['title'])
        self.display.frame_period = 1.0 / float(self.config['framerate'])
        self.display.show_stats = self.config['stats']
        self.display.repeat = self.config['repeat']
        self.display.sync = self.config['sync']

    def transform(self, in_frame, out_frame):
        numpy_image = in_frame.as_numpy(dtype=numpy.uint8)
        if not numpy_image.flags.contiguous:
            numpy_image = numpy.ascontiguousarray(numpy_image)
        self.update_config()
        h, w, bpc = numpy_image.shape
        w = (w * self.config['expand']) // self.config['shrink']
        h = (h * self.config['expand']) // self.config['shrink']
        if self.display_size != (w, h):
            self.display_size = w, h
            self.display.setMinimumSize(w, h)
            if not self.isVisible():
                self.show()
        if bpc == 3:
            if in_frame.type != 'RGB' and in_frame.type != self.last_frame_type:
                self.logger.warning(
                    'Expected RGB input, got %s', in_frame.type)
        elif bpc == 1:
            if in_frame.type != 'Y' and in_frame.type != self.last_frame_type:
                self.logger.warning(
                    'Expected Y input, got %s', in_frame.type)
        else:
            self.logger.critical(
                'Cannot display %s frame with %d components', in_frame.type, bpc)
            return False
        self.last_frame_type = in_frame.type
        self.display.in_queue.append((in_frame, numpy_image))
        return True
