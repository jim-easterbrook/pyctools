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

"""Simple Qt display.

Shows incoming images in a Qt window.

"""

__all__ = ['QtDisplay']

from collections import deque
import sys

import numpy
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

from pyctools.core import ConfigInt, Transformer

class SimpleDisplay(QtGui.QLabel):
    def __init__(self, *arg, **kw):
        super(SimpleDisplay, self).__init__(*arg, **kw)
        self.in_queue = deque()
        self.framerate = 25
        # start timer to show frames at regular intervals
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.timer_show_frame)
        self.timer.start(1000 // self.framerate)

    def show_frame(self, frame, image, framerate):
        # this method will be called from another thread, so do
        # nothing except put stuff on queue
        self.in_queue.append((frame, image, framerate))

    def timer_show_frame(self):
        if not self.in_queue:
            return
        frame, image, framerate = self.in_queue.popleft()
        if framerate != self.framerate:
            self.framerate = framerate
            self.timer.setInterval(1000 // self.framerate)
        if not self.isVisible():
            self.show()
        pixmap = QtGui.QPixmap.fromImage(image)
        self.resize(pixmap.size())
        self.setPixmap(pixmap)

    def shut_down(self):
        self.timer.stop()
        self.close()

class QtDisplay(Transformer):
    def initialise(self):
        self.config['shrink'] = ConfigInt(min_value=1, dynamic=True)
        self.config['expand'] = ConfigInt(min_value=1, dynamic=True)
        self.config['framerate'] = ConfigInt(min_value=1, value=25)
        self.last_frame_type = None
        self.display = SimpleDisplay(None, Qt.Window | Qt.WindowStaysOnTopHint)

    def transform(self, in_frame, out_frame):
        self.update_config()
        shrink = self.config['shrink']
        expand = self.config['expand']
        framerate = self.config['framerate']
        numpy_image = in_frame.as_numpy(dtype=numpy.uint8, dstack=True)[0]
        ylen, xlen, bpc = numpy_image.shape
        if bpc == 3:
            if in_frame.type != 'RGB' and in_frame.type != self.last_frame_type:
                self.logger.warning('Expected RGB input, got %s', in_frame.type)
            image = QtGui.QImage(numpy_image.data, xlen, ylen, xlen * bpc,
                                 QtGui.QImage.Format_RGB888)
        elif bpc == 1:
            if in_frame.type != 'Y' and in_frame.type != self.last_frame_type:
                self.logger.warning('Expected Y input, got %s', in_frame.type)
            image = QtGui.QImage(numpy_image.data, xlen, ylen, xlen,
                                 QtGui.QImage.Format_Indexed8)
            image.setNumColors(256)
            for i in range(256):
                image.setColor(i, QtGui.qRgba(i, i, i, 255))
        else:
            self.logger.critical(
                'Cannot display %s frame with %d components', in_frame.type, bpc)
            return False
        self.last_frame_type = in_frame.type
        if shrink > 1 or expand > 1:
            image = image.scaled(
                xlen * expand // shrink, ylen * expand // shrink,
                transformMode=Qt.SmoothTransformation)
        self.display.show_frame(in_frame, image, framerate)
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
