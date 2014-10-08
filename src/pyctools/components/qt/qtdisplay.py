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

import copy
import logging
import sys

from guild.actor import *
from guild.qtactor import ActorSignal, QtActorMixin
import numpy
from PyQt4 import QtGui, QtCore

from ...core import ConfigMixin

class QtDisplay(QtActorMixin, QtGui.QLabel, ConfigMixin):
    def __init__(self):
        super(QtDisplay, self).__init__(None, QtCore.Qt.Window)
        ConfigMixin.__init__(self)
        self.show()

    @actor_method
    def input(self, frame):
        if not frame:
            self.close()
            self.stop()
            return
        numpy_image = frame.as_numpy()[0]
        if numpy_image.dtype != numpy.uint8:
            numpy_image = numpy_image.clip(0, 255).astype(numpy.uint8)
        ylen, xlen, bpc = numpy_image.shape
        image = QtGui.QImage(numpy_image.data, xlen, ylen, xlen * bpc,
                             QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(image)
        self.resize(xlen, ylen)
        self.setPixmap(pixmap)

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
