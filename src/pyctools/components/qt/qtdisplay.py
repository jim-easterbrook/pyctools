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

Note: this (currently) requires my branch of guild:
https://github.com/jim-easterbrook/guild which adds Qt support.

"""

__all__ = ['QtDisplay']

from collections import deque
import copy
import logging
import sys

from guild.actor import *
from guild.qtactor import ActorSignal, QtActorMixin
import numpy
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

from ...core import ConfigMixin, ConfigInt

class QtDisplay(QtActorMixin, QtGui.QLabel, ConfigMixin):
    inputs = ['input']
    outputs = []

    def __init__(self):
        super(QtDisplay, self).__init__(
            None, Qt.Window | Qt.WindowStaysOnTopHint)
        ConfigMixin.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config['shrink'] = ConfigInt(min_value=1, dynamic=True)
        self.config['expand'] = ConfigInt(min_value=1, dynamic=True)
        self.config['framerate'] = ConfigInt(min_value=1, value=25)
        self.timer = QtCore.QTimer(self)

    def process_start(self):
        self.next_frame = deque()
        # start timer to show frames at regular intervals
        self.timer.timeout.connect(self.show_frame)
        self.timer.start(1000 // self.config['framerate'])

    @actor_method
    def input(self, frame):
        self.next_frame.append(frame)

    def show_frame(self):
        if not self.next_frame:
            return
        self.timer.setInterval(1000 // self.config['framerate'])
        frame = self.next_frame.popleft()
        if not frame:
            self.stop()
            return
        if not self.isVisible():
            self.show()
        numpy_image = frame.as_numpy(numpy.uint8)[0]
        if frame.type == 'RGB':
            ylen, xlen, bpc = numpy_image.shape
            image = QtGui.QImage(numpy_image.data, xlen, ylen, xlen * bpc,
                                 QtGui.QImage.Format_RGB888)
        elif frame.type == 'Y':
            ylen, xlen = numpy_image.shape
            image = QtGui.QImage(numpy_image.data, xlen, ylen, xlen,
                                 QtGui.QImage.Format_Indexed8)
            image.setNumColors(256)
            for i in range(256):
                image.setColor(i, QtGui.qRgba(i, i, i, 255))
        else:
            self.logger.critical('Cannot display %s frame', frame.type)
            self.stop()
            return
        pixmap = QtGui.QPixmap.fromImage(image)
        shrink = self.config['shrink']
        expand = self.config['expand']
        if shrink > 1 or expand > 1:
            pixmap = pixmap.scaled(
                xlen * expand // shrink, ylen * expand // shrink)
        self.resize(pixmap.size())
        self.setPixmap(pixmap)

    def onStop(self):
        super(QtDisplay, self).onStop()
        self.timer.stop()
        self.close()

def main():
    from ..io.rawfilereader import RawFileReader
    from ..colourspace.yuvtorgb import YUVtoRGB

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
