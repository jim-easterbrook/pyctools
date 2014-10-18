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

"""Video file reader.

Reads conventional video files (mp4, flv, etc. depends on installed
GStreamer plugins).

"""

from __future__ import print_function

__all__ = ['VideoFileReader']

import logging
import os
import sys

import cv2
from guild.actor import *

from ...core import Metadata, Component, ConfigPath, ConfigEnum

class VideoFileReader(Component):
    inputs = []

    def __init__(self):
        super(VideoFileReader, self).__init__(with_outframe_pool=True)
        self.config['path'] = ConfigPath()
        self.config['looping'] = ConfigEnum(('off', 'repeat'), dynamic=True)

    def process_start(self):
        super(VideoFileReader, self).process_start()
        self.update_config()
        path = self.config['path']
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            self.logger.critical('Failed to open %s', path)
            self.output(None)
            self.stop()
        self.metadata = Metadata().from_file(path)
        self.frame_no = 0

    @actor_method
    def new_out_frame(self, frame):
        self.update_config()
        OK, data = self.cap.read()
        if not OK:
            if self.frame_no == 0 or self.config['looping'] == 'off':
                self.output(None)
                self.stop()
                return
            self.cap.release()
            path = self.config['path']
            self.cap = cv2.VideoCapture(path)
            OK, data = self.cap.read()
            if not OK:
                self.logger.critical('Cannot repeat file')
                self.output(None)
                self.stop()
                return
        frame.data = [cv2.cvtColor(data, cv2.COLOR_BGR2RGB)]
        frame.type = 'RGB'
        frame.frame_no = self.frame_no
        self.frame_no += 1
        frame.metadata.copy(self.metadata)
        self.output(frame)

    def onStop(self):
        super(VideoFileReader, self).onStop()
        self.cap.release()

def main():
    from PyQt4 import QtGui
    from ..qt.qtdisplay import QtDisplay

    if len(sys.argv) != 2:
        print('usage: %s video_file' % sys.argv[0])
        return 1
    logging.basicConfig(level=logging.DEBUG)
    print('VideoFileReader demonstration')
    app = QtGui.QApplication([])
    source = VideoFileReader()
    config = source.get_config()
    config['path'] = sys.argv[1]
    config['looping'] = 'repeat'
    source.set_config(config)
    sink = QtDisplay()
    pipeline(source, sink)
    start(source, sink)
    try:
        app.exec_()
    finally:
        stop(source, sink)
        wait_for(source, sink)
    return 0

if __name__ == '__main__':
    sys.exit(main())
