#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2015  Pyctools contributors
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

"""Display image hostograms in a Qt window.

The histogram display is normalised so each component uses the full
Y-axis range. The X-axis covers the range [0, 256). Values outside this
range are counted and the results displayed as raw numbers and
percentage of pixels.

=========  ===  ====
Config
=========  ===  ====
``title``  str  Window title.
``log``    str  Use logarithmic Y axis. Can be ``'off'`` or ``'on'``.
=========  ===  ====

"""

__all__ = ['ShowHistogram']
__docformat__ = 'restructuredtext en'

import math

import numpy

from pyctools.core.config import ConfigEnum, ConfigStr
from pyctools.core.base import Transformer
from pyctools.core.qt import Qt, QtEventLoop, QtGui

class ShowHistogram(Transformer, QtGui.QWidget):
    event_loop = QtEventLoop

    def __init__(self, **config):
        super(ShowHistogram, self).__init__(**config)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setLayout(QtGui.QFormLayout())
        # main histogram display
        self.display = QtGui.QLabel()
        self.display.setPixmap(QtGui.QPixmap(256, 100))
        self.display.pixmap().fill(Qt.white)
        self.layout().addRow(self.display)
        # positive clip count
        self.pos_clips = QtGui.QLabel()
        self.layout().addRow('Positive clip count', self.pos_clips)
        self.pos_clip_percent = QtGui.QLabel()
        self.layout().addRow('%', self.pos_clip_percent)
        # negative clip count
        self.neg_clips = QtGui.QLabel()
        self.layout().addRow('Negative clip count', self.neg_clips)
        self.neg_clip_percent = QtGui.QLabel()
        self.layout().addRow('%', self.neg_clip_percent)

    def initialise(self):
        self.config['title'] = ConfigStr()
        self.config['log'] = ConfigEnum(('off', 'on'))

    def closeEvent(self, event):
        event.accept()
        self.stop()

    def on_start(self):
        self.show()
        self.on_set_config()

    def on_set_config(self):
        self.update_config()
        self.setWindowTitle(self.config['title'])

    def transform(self, in_frame, out_frame):
        self.update_config()
        log = self.config['log'] == 'on'
        data = in_frame.as_numpy()
        h, w, comps = data.shape
        # generate histogram
        if comps == 3:
            colours = (0xff0000, 0x00ff00, 0x0000ff)
        else:
            colours = (0,) * comps
        q_image = QtGui.QImage(256, 100, QtGui.QImage.Format_RGB888)
        q_image.fill(Qt.white)
        pos_clips = []
        neg_clips = []
        for comp in range(comps):
            histogram, edges = numpy.histogram(
                data[:,:,comp], bins=256, range=(0.0, 256.0))
            max_value = float(1 + max(histogram))
            colour = colours[comp]
            for x in range(len(histogram)):
                y = float(1 + histogram[x]) / max_value
                if log:
                    y = max(0.0, 1.0 + (math.log10(y) / 5.0))
                y *= 98.0
                q_image.setPixel(x, 99 - y, colour)
                q_image.setPixel(x, 98 - y, colour)
            pos_clips.append(numpy.count_nonzero(data[:,:,comp] >= 256.0))
            neg_clips.append(numpy.count_nonzero(data[:,:,comp] < 0.0))
        pixmap = QtGui.QPixmap.fromImage(q_image)
        self.display.setPixmap(pixmap)
        self.pos_clips.setText(','.join(['{:8d}'.format(x) for x in pos_clips]))
        self.pos_clip_percent.setText(', '.join(['{:.3f}'.format(
            float(x * 100) / float(h * w)) for x in pos_clips]))
        self.neg_clips.setText(','.join(['{:8d}'.format(x) for x in neg_clips]))
        self.neg_clip_percent.setText(', '.join(['{:.3f}'.format(
            float(x * 100) / float(h * w)) for x in neg_clips]))
        return True
