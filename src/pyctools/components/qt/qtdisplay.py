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
within OpenGL.

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
``sync``       str  Synchronise to video card frame rate. Can be ``'off'`` or ``'on'``.
``stats``      str  Show actual frame rate statistics. Can be ``'off'`` or ``'on'``.
=============  ===  ====

"""

__all__ = ['QtDisplay']
__docformat__ = 'restructuredtext en'

from collections import deque
import time

from guild.actor import actor_method
from guild.qtactor import QtActorMixin
import numpy
from OpenGL import GL
from PyQt4 import QtGui, QtCore, QtOpenGL
from PyQt4.QtCore import Qt

from pyctools.core.config import ConfigInt, ConfigEnum
from pyctools.core.base import Transformer

class BufferSwapper(QtCore.QObject):
    done_swap = QtCore.pyqtSignal(float)

    def __init__(self, widget, parent=None):
        super(BufferSwapper, self).__init__(parent)
        self.widget = widget

    @QtCore.pyqtSlot()
    def swap(self):
        self.widget.makeCurrent()
        self.widget.swapBuffers()
        now = time.time()
        self.widget.doneCurrent()
        self.done_swap.emit(now)


class SimpleDisplay(QtActorMixin, QtOpenGL.QGLWidget):
    do_swap = QtCore.pyqtSignal()

    def __init__(self, owner, parent=None, flags=0):
        super(SimpleDisplay, self).__init__(parent, None, flags)
        self.owner = owner
        self.in_queue = deque()
        self.in_frame = None
        self.setAutoBufferSwap(False)
        # if user has set "tear free video" or similar, we might not
        # want to increase swap interval any further
        fmt = self.format()
        fmt.setSwapInterval(0)
        self.setFormat(fmt)
        display_freq = self.measure_display_rate()
        if display_freq > 500:
            # unfeasibly fast => not synchronised
            fmt.setSwapInterval(1)
            self.setFormat(fmt)
            display_freq = self.measure_display_rate()
            self.sync_swap_interval = 1
        else:
            self.sync_swap_interval = 0
        if display_freq > 500:
            self.owner.logger.warning('Unable to synchronise to video frame rate')
            display_freq = 60
            self.sync_swap_interval = -1
        self.sync_swap = self.sync_swap_interval >= 0
        self._display_period = 1.0 / float(display_freq)
        self._frame_period = 1.0 / 25.0
        self._next_frame_due = 0.0
        self._swapping = False
        self.last_frame_type = None
        # create timer to show frames at regular intervals
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.display_frame)
        # create separate thread to swap buffers
        self.swapper_thread = QtCore.QThread()
        self.swapper = BufferSwapper(self)
        self.swapper.moveToThread(self.swapper_thread)
        self.do_swap.connect(self.swapper.swap)
        self.swapper.done_swap.connect(self.done_swap)
        self.swapper_thread.start()

    def measure_display_rate(self):
        self.makeCurrent()
        self.swapBuffers()
        start = time.time()
        for n in range(5):
            self.swapBuffers()
        display_freq = int(0.5 + (5.0 / (time.time() - start)))
        self.doneCurrent()
        return display_freq

    def onStop(self):
        super(SimpleDisplay, self).onStop()
        self.timer.stop()
        self.swapper.blockSignals(True)
        self.swapper_thread.quit()
        self.swapper_thread.wait()
        self.close()

    def closeEvent(self, event):
        self.stop()

    @actor_method
    def show_frame(self, frame):
        self.in_queue.append(frame)
        if self._swapping or len(self.in_queue) > 1:
            # no need to set timer
            return
        if self._next_frame_due:
            now = time.time()
        else:
            # initialise
            self.makeCurrent()
            self.swapBuffers()
            self.swapBuffers()
            now = time.time()
            self._next_frame_due = now
            self._display_clock = now
            self._frame_count = -2
        if self._next_frame_due > now + self._frame_period:
            # set timer to show frame later
            sleep = self._next_frame_due - now
            self.timer.start(int(sleep * 1000.0))
        else:
            # show frame immmediately
            self.display_frame()

    @QtCore.pyqtSlot(float)
    def done_swap(self, now):
        self._swapping = False
        self.timer.stop()
        margin = self._display_period / 2.0
        # adjust display clock
        while self._display_clock < now - margin:
            self._display_clock += self._display_period
        if self.sync_swap and self.sync_swap_interval >= 0:
            error = self._display_clock - now
            self._display_clock -= error / 100.0
            self._display_period -= error / 10000.0
        # adjust frame clock
        while self._next_frame_due < self._display_clock - margin:
            self._next_frame_due += self._display_period
        if self.sync_swap and self.sync_swap_interval >= 0:
            error = self._next_frame_due - self._display_clock
            while error > margin:
                error -= self._display_period
            if abs(error) < self._frame_period * self._display_period / 4.0:
                self._next_frame_due -= error
        if not self.in_queue:
            # nothing to do
            return
        if self._next_frame_due > self._display_clock + self._display_period:
            # set timer to show frame later
            skip_frames = int(
                (self._next_frame_due - self._display_clock) /
                self._display_period)
            sleep = (self._display_clock + (skip_frames * self._display_period)
                     - time.time())
            self.timer.start(int(sleep * 1000.0))
        else:
            # show frame immmediately
            self.display_frame()

    @QtCore.pyqtSlot()
    def display_frame(self):
        # get latest config
        self.owner.update_config()
        framerate = self.owner.config['framerate']
        self._frame_period = 1.0 / float(framerate)
        stats = self.owner.config['stats'] == 'on'
        shrink = self.owner.config['shrink']
        expand = self.owner.config['expand']
        scale = float(expand) / float(shrink)
        sync = self.owner.config['sync'] == 'on'
        if sync != self.sync_swap:
            self.sync_swap = sync
            if self.sync_swap_interval >= 0:
                fmt = self.format()
                fmt.setSwapInterval(self.sync_swap_interval)
                self.setFormat(fmt)
        # get frame to show
        self.in_frame = self.in_queue.popleft()
        self._next_frame_due += self._frame_period
        self._frame_count += 1
        if self._frame_count <= 0:
            self._block_start = self._next_frame_due
        if self._next_frame_due - self._block_start > 5.0:
            if stats:
                frame_rate = float(self._frame_count) / (
                    self._next_frame_due - self._block_start)
                self.owner.logger.warning(
                    'Average frame rate: %.2fHz', frame_rate)
            self._frame_count = 0
            self._block_start = self._next_frame_due
        h, w = self.in_frame.size()
        self.resize(w * scale, h * scale)
        if not self.isVisible():
            self.show()
        self.updateGL()
        self.doneCurrent()
        self._swapping = True
        self.do_swap.emit()

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
        if not self.in_frame:
            return
        numpy_image = self.in_frame.as_numpy(dtype=numpy.uint8)
        if not numpy_image.flags.contiguous:
            numpy_image = numpy.ascontiguousarray(numpy_image)
        ylen, xlen, bpc = numpy_image.shape
        if bpc == 3:
            if (self.in_frame.type != 'RGB' and
                        self.in_frame.type != self.last_frame_type):
                self.owner.logger.warning(
                    'Expected RGB input, got %s', self.in_frame.type)
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB, xlen, ylen,
                            0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, numpy_image)
        elif bpc == 1:
            if (self.in_frame.type != 'Y' and
                        self.in_frame.type != self.last_frame_type):
                self.owner.logger.warning(
                    'Expected Y input, got %s', self.in_frame.type)
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB, xlen, ylen,
                            0, GL.GL_LUMINANCE, GL.GL_UNSIGNED_BYTE, numpy_image)
        else:
            self.owner.logger.critical(
                'Cannot display %s frame with %d components',
                self.in_frame.type, bpc)
            self.owner.stop()
            return
        self.last_frame_type = self.in_frame.type
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


class QtDisplay(Transformer):
    def initialise(self):
        self.config['shrink'] = ConfigInt(min_value=1, dynamic=True)
        self.config['expand'] = ConfigInt(min_value=1, dynamic=True)
        self.config['framerate'] = ConfigInt(min_value=1, value=25)
        self.config['sync'] = ConfigEnum(('off', 'on'))
        self.config['sync'] = 'on'
        self.config['stats'] = ConfigEnum(('off', 'on'))
        self.display = SimpleDisplay(
            self, None, Qt.Window | Qt.WindowStaysOnTopHint)

    def start(self):
        super(QtDisplay, self).start()
        self.display.start()

    def stop(self):
        super(QtDisplay, self).stop()
        self.display.stop()

    def join(self):
        super(QtDisplay, self).join()
        self.display.join()

    def transform(self, in_frame, out_frame):
        self.display.show_frame(in_frame)
        return True
