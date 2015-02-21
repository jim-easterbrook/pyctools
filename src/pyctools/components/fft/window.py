#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-15  Pyctools contributors
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

"""FFT window functions.

Window functions are used with Fourier transforms to give some control
over the trade-off between frequency resolution and "leakage". See
`Wikipedia <http://en.wikipedia.org/wiki/Window_function>`_ for a good
introduction to the subject.

This module contains components to generate several popular window
functions, and one to generate a corresponding "inverse window". This
can be used to reconstruct a signal from its Fourier transform. Note
that overlapping tiles are almost essential to avoid visible tile edge
effects when doing this. The inverse windows compensate for the
attenuation of the original window and "cross fade" from one tile to
the next, overlapping, tile. There is a choice of crossfade function.

For each window function component there is a "core" function. This
generates a single :py:class:`~pyctools.core.frame.Frame` containing
the window data. This is useful if you don't need to change the window
while your network of components is running. For example::

    window = Modulate()
    window.cell(HammingCore(xtile=32, ytile=32))

creates a windowing component that uses a 32x32 Hamming window. Its
``cell`` input does not need to be connected to anything.

.. autosummary::
   :nosignatures:

   Hann
   HannCore
   Hamming
   HammingCore
   Blackman
   BlackmanCore
   Kaiser
   KaiserCore
   InverseWindow

"""

__all__ = ['Hann', 'Hamming', 'Blackman', 'Kaiser', 'InverseWindow']
__docformat__ = 'restructuredtext en'

import math
import numpy
import scipy.special
import sys
import time
if 'sphinx' in sys.modules:
    __all__ += ['HannCore', 'HammingCore', 'BlackmanCore', 'KaiserCore']

from pyctools.core.base import Component
from pyctools.core.config import ConfigEnum, ConfigFloat, ConfigInt
from pyctools.core.frame import Frame

class WindowBase(Component):
    inputs = []

    def initialise(self):
        self.config['xtile'] = ConfigInt(min_value=1, dynamic=True)
        self.config['ytile'] = ConfigInt(min_value=1, dynamic=True)

    def on_connect(self, output_name):
        # send first window
        self.update_config()
        self.make_window()

    def gen_process(self):
        # send more windows if config changes
        while True:
            yield 1
            time.sleep(0.1)
            if self.update_config():
                self.make_window()


class Hann(WindowBase):
    """Hann window.

    ===========  ===  ====
    Config
    ===========  ===  ====
    ``xtile``    int  Horizontal tile size.
    ``ytile``    int  Vertical tile size.
    ===========  ===  ====

    """
    def make_window(self):
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        self.output(HannCore(x_tile=x_tile, y_tile=y_tile))


class Hamming(WindowBase):
    """Hamming window.

    ===========  ===  ====
    Config
    ===========  ===  ====
    ``xtile``    int  Horizontal tile size.
    ``ytile``    int  Vertical tile size.
    ===========  ===  ====

    """
    def make_window(self):
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        self.output(HammingCore(x_tile=x_tile, y_tile=y_tile))


class Blackman(WindowBase):
    """Blackman window.

    ===========  =====  ====
    Config
    ===========  =====  ====
    ``xtile``    int    Horizontal tile size.
    ``ytile``    int    Vertical tile size.
    ``alpha``    float  Window control parameter.
    ===========  =====  ====

    """
    def initialise(self):
        super(Blackman, self).initialise()
        self.config['alpha'] = ConfigFloat(value=0.16, dynamic=True)

    def make_window(self):
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        alpha = self.config['alpha']
        self.output(BlackmanCore(x_tile=x_tile, y_tile=y_tile, alpha=alpha))


class Kaiser(WindowBase):
    """Kaiser-Bessel window.

    ===========  =====  ====
    Config
    ===========  =====  ====
    ``xtile``    int    Horizontal tile size.
    ``ytile``    int    Vertical tile size.
    ``alpha``    float  Window control parameter.
    ===========  =====  ====

    """
    def initialise(self):
        super(Kaiser, self).initialise()
        self.config['alpha'] = ConfigFloat(value=3.0, dynamic=True)

    def make_window(self):
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        alpha = self.config['alpha']
        self.output(KaiserCore(x_tile=x_tile, y_tile=y_tile, alpha=alpha))


def Window2D(name, x_tile, y_tile, function_1D, x_params={}, y_params={}):
    if x_tile == 1:
        x_win = numpy.array([1.0], dtype=numpy.float32)
    else:
        x_win = function_1D(x_tile, **x_params)
    if y_tile == 1:
        y_win = numpy.array([1.0], dtype=numpy.float32)
    else:
        y_win = function_1D(y_tile, **y_params)
    result = numpy.empty(
        [1, y_win.shape[0], x_win.shape[0], 1], dtype=numpy.float32)
    for y in range(result.shape[1]):
        for x in range(result.shape[2]):
            result[0, y, x, 0] = x_win[x] * y_win[y]
    out_frame = Frame()
    out_frame.data = result
    out_frame.type = 'win'
    audit = out_frame.metadata.get('audit')
    audit += 'data = %sWindow()\n' % name
    audit += '    size: %d x %d\n' % (y_tile, x_tile)
    extras = []
    for key, value in x_params.items():
        extras.append('%s: %s' % (key, str(value)))
    if extras:
        audit += '    horiz params: %s\n' % (', '.join(extras))
    extras = []
    for key, value in y_params.items():
        extras.append('%s: %s' % (key, str(value)))
    if extras:
        audit += '    vert params: %s\n' % (', '.join(extras))
    out_frame.metadata.set('audit', audit)
    return out_frame


def HannCore(x_tile=1, y_tile=1):
    def Hann_1D(tile):
        result = numpy.ndarray([tile], dtype=numpy.float32)
        for i in range(tile):
            result[i] = 0.5 + (0.5 * math.cos(
                math.pi * float((i * 2) + tile - 1) / float(tile - 1)))
        return result

    return Window2D('Hann', x_tile, y_tile, Hann_1D)


def HammingCore(x_tile=1, y_tile=1):
    def Hamming_1D(tile):
        result = numpy.ndarray([tile], dtype=numpy.float32)
        for i in range(tile):
            result[i] = 0.53836 + (0.46164 * math.cos(
                math.pi * float((i * 2) + tile - 1) / float(tile - 1)))
        return result

    return Window2D('Hamming', x_tile, y_tile, Hamming_1D)


def BlackmanCore(x_tile=1, y_tile=1, alpha=0.16):
    def Blackman_1D(tile, alpha):
        result = numpy.ndarray([tile], dtype=numpy.float32)
        a0 = (1.0 - alpha) / 2.0
        a1 = -1.0 / 2.0
        a2 = alpha / 2.0
        for i in range(tile):
            f = math.pi * float(i * 2) / float(tile - 1)
            result[i] = a0 + (a1 * math.cos(f)) + (a2 * math.cos(2.0 * f))
        return result

    return Window2D('Blackman', x_tile, y_tile, Blackman_1D,
                    x_params={'alpha' : alpha}, y_params={'alpha' : alpha})


def KaiserCore(x_tile=1, y_tile=1, alpha=3.0):
    def Kaiser_1D(tile, alpha):
        result = numpy.ndarray([tile], dtype=numpy.float32)
        d = scipy.special.i0(math.pi * alpha)
        for i in range(tile):
            f = float(i * 2) / float(tile - 1)
            f = 1.0 - ((f - 1.0) ** 2.0)
            f = math.sqrt(f)
            result[i] = scipy.special.i0(math.pi * alpha * f) / d
        return result

    return Window2D('Kaiser', x_tile, y_tile, Kaiser_1D,
                    x_params={'alpha' : alpha}, y_params={'alpha' : alpha})


class InverseWindow(Component):
    """Generate "inverse" window function with inter-tile cross-fade.

    The ``fade`` config value determines the transition from one tile
    to the next, within their area of overlap. ``'switch'`` abruptly
    cuts from one tile to the next, ``'linear'`` does a cross-fade and
    ``'minsnr'`` does a weighted cross-fade to minimise signal to
    noise ratio.

    =========  ===  ====
    Config
    =========  ===  ====
    ``xtile``  int  Horizontal tile size.
    ``ytile``  int  Vertical tile size.
    ``xoff``   int  Horizontal tile offset. Typically set to xtile / 2.
    ``yoff``   int  Vertical tile offset. Typically set to ytile / 2.
    ``fade``   str  Can be ``'switch'``, ``'linear'`` or ``'minsnr'``.
    =========  ===  ====

    """
    outputs = ['window', 'inv_window']
    with_outframe_pool = False

    def initialise(self):
        self.config['xtile'] = ConfigInt(min_value=1, dynamic=True)
        self.config['ytile'] = ConfigInt(min_value=1, dynamic=True)
        self.config['xoff'] = ConfigInt(min_value=1, dynamic=True)
        self.config['yoff'] = ConfigInt(min_value=1, dynamic=True)
        self.config['fade'] = ConfigEnum(choices=(
            'switch', 'linear', 'minsnr'), dynamic=True)

    def process_frame(self):
        self.update_config()
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        x_off = self.config['xoff']
        y_off = self.config['yoff']
        fade = self.config['fade']
        in_frame = self.input_buffer['input'].get()
        self.window(in_frame)
        out_frame = Frame()
        out_frame.initialise(in_frame)
        audit = out_frame.metadata.get('audit')
        audit += 'data = InverseWindow(data)\n'
        audit += '    size: %d x %d, offset: %d x %d\n' % (
            y_tile, x_tile, y_off, x_off)
        audit += '    fade: %s\n' % fade
        out_frame.metadata.set('audit', audit)

        in_data = in_frame.as_numpy(dtype=numpy.float32)
        result = numpy.empty(in_data.shape, dtype=numpy.float32)
        x_overlap = x_tile - x_off
        y_overlap = y_tile - y_off
        for y in range(y_tile):
            y0 = y
            while y0 >= y_off:
                y0 -= y_off
            for x in range(x_tile):
                x0 = x
                while x0 >= x_off:
                    x0 -= x_off
                # get window value of this and neighbouring tiles
                centre = in_data[0, y, x, 0]
                neighbours = []
                for j in range(y0, y_tile, y_off):
                    for i in range(x0, x_tile, x_off):
                        if j == y and i == x:
                            continue
                        neighbours.append(in_data[0, j, i, 0])
                if not neighbours:
                    result[0, y, x, 0] = 1.0 / max(centre, 0.000001)
                elif fade == 'minsnr':
                    result[0, y, x, 0] = centre / (
                        (centre ** 2) + sum(map(lambda x: x ** 2, neighbours)))
                elif fade == 'linear':
                    result[0, y, x, 0] = 1.0 / (centre + sum(neighbours))
                else:
                    biggest = max(neighbours)
                    if centre > biggest:
                        result[0, y, x, 0] = 1.0 / max(centre, 0.000001)
                    elif centre < biggest:
                        result[0, y, x, 0] = 0.0
                    else:
                        result[0, y, x, 0] = 0.5 / max(centre, 0.000001)
        out_frame.data = result
        self.inv_window(out_frame)
