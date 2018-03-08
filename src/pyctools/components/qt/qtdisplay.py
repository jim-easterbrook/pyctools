#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-18  Pyctools contributors
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
from contextlib import contextmanager
import threading
import time

import numpy
from OpenGL import GL
from PyQt5 import QtCore, QtGui, QtOpenGL, QtWidgets
from PyQt5.QtCore import Qt

from pyctools.core.config import ConfigBool, ConfigInt, ConfigStr
from pyctools.core.base import Transformer
from pyctools.core.qt import qt_version_info, QtEventLoop

# single context lock to serialise OpenGL operations across multiple
# windows
ctx_lock = threading.RLock()

@contextmanager
def context():
    ctx_lock.acquire()
    yield
    ctx_lock.release()

class RenderingThread(QtCore.QObject):
    next_frame_event = QtCore.QEvent.registerEventType()

    def __init__(self, widget, **kwds):
        super(RenderingThread, self).__init__(**kwds)
        self.widget = widget
        self.running = False

    def next_frame(self):
        self.widget.makeCurrent()
        self.widget.paintGL()
        # swapBuffers should block until frame interval, depending on hardware
        self.widget.swapBuffers()
        now = time.time()
        self.clock += 1.0 / 75.0
        while now < self.clock:
            # swapBuffers didn't block, so do our own free running at 75Hz
            time.sleep(self.clock - now)
            now = time.time()
        self.widget.done_swap(now)
        # schedule next frame, after processing other events
        QtCore.QCoreApplication.postEvent(
            self, QtCore.QEvent(self.next_frame_event), Qt.LowEventPriority)

    def event(self, event):
        if event.type() == self.next_frame_event:
            event.accept()
            self.next_frame()
            return True
        return super(RenderingThread, self).event(event)

    @QtCore.pyqtSlot(object)
    def resize(self, event):
        # resize event is always sent when window first becomes visible
        if not self.running:
            self.widget.makeCurrent()
            self.widget.glInit()
            self.clock = time.time()
        super(GLDisplayOld, self.widget).resizeEvent(event)
        if not self.running:
            self.running = True
            self.next_frame()


class GLDisplayCommon(object):
    def __init__(self, *arg, **kwds):
        super(GLDisplayCommon, self).__init__(*arg, **kwds)
        self.in_queue = deque()
        self.black_image = numpy.zeros((1, 1, 1), dtype=numpy.uint8)
        self.show_black = True
        self.paused = False
        self._display_period = 0.0
        self._frame_count = -10
        self.frame_period = 1.0 / 25.0
        self._clock_history = deque(maxlen=100)

    @QtCore.pyqtSlot(float)
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
        with context():
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            GL.glDisable(GL.GL_DEPTH_TEST)
            GL.glEnable(GL.GL_TEXTURE_2D)
            texture = GL.glGenTextures(1)
            GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
            GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
            GL.glDisable(GL.GL_TEXTURE_2D)

    def resizeGL(self, w, h):
        with context():
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
        with context():
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


class GLDisplayOld(GLDisplayCommon, QtOpenGL.QGLWidget):
    resize_event = QtCore.pyqtSignal(object)

    def __init__(self, logger, fmt, **kwds):
        super(GLDisplayOld, self).__init__(fmt, **kwds)
        self.logger = logger
        self.setAutoBufferSwap(False)
        # create separate rendering thread
        self.render_thread = QtCore.QThread()
        self.render = RenderingThread(self)
        self.render.moveToThread(self.render_thread)
        self.resize_event.connect(self.render.resize)

    def startup(self):
        self.doneCurrent()
        if qt_version_info >= (5,):
            self.context().moveToThread(self.render_thread)
        self.render_thread.start()

    def shutdown(self):
        self.render_thread.quit()
        self.render_thread.wait()

    def resizeEvent(self, event):
        if self.render_thread.isRunning():
            self.resize_event.emit(event)
        else:
            super(GLDisplayOld, self).resizeEvent(event)

    def paintEvent(self, event):
        # ignore paint events as widget is redrawn every frame period anyway
        return


class GLDisplayNew(GLDisplayCommon, QtWidgets.QOpenGLWidget):
    def __init__(self, logger, **kwds):
        super(GLDisplayNew, self).__init__(**kwds)
        self.logger = logger
        self.frameSwapped.connect(self.frame_swapped)

    def startup(self):
        pass

    def shutdown(self):
        pass

    @QtCore.pyqtSlot()
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
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setLayout(QtWidgets.QGridLayout())
        if qt_version_info >= (5, 4):
            fmt = QtGui.QSurfaceFormat()
            fmt.setProfile(QtGui.QSurfaceFormat.CompatibilityProfile)
            fmt.setSwapBehavior(QtGui.QSurfaceFormat.DoubleBuffer)
            fmt.setSwapInterval(1)
            self.display = GLDisplayNew(self.logger)
            self.display.setFormat(fmt)
        else:
            fmt = QtOpenGL.QGLFormat()
            fmt.setProfile(QtOpenGL.QGLFormat.CompatibilityProfile)
            fmt.setDoubleBuffer(True)
            fmt.setSwapInterval(1)
            self.display = GLDisplayOld(self.logger, fmt)
        self.layout().addWidget(self.display, 0, 0, 1, 4)
        # control buttons
        self.pause_button = QtWidgets.QPushButton('pause')
        self.pause_button.setShortcut(Qt.Key_Space)
        self.pause_button.clicked.connect(self.pause)
        self.layout().addWidget(self.pause_button, 1, 0)
        self.step_button = QtWidgets.QPushButton('step')
        self.step_button.setShortcut(QtGui.QKeySequence.MoveToNextChar)
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
