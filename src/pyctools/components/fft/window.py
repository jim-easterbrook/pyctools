#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-19  Pyctools contributors
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

__all__ = ['Window', 'Hann', 'Hamming', 'Blackman', 'Kaiser', 'InverseWindow']
__docformat__ = 'restructuredtext en'

from collections import OrderedDict
import math
import numpy
import sys
if 'sphinx' in sys.modules:
    __all__ += ['HannCore', 'HammingCore', 'BlackmanCore', 'KaiserCore']

from pyctools.core.base import Component
from pyctools.core.config import ConfigBool, ConfigEnum, ConfigFloat, ConfigInt
from pyctools.core.frame import Frame
from pyctools.core.types import pt_float

class WindowBase(Component):
    inputs = []
    with_outframe_pool = False

    def initialise(self):
        self.config['xtile'] = ConfigInt(min_value=1)
        self.config['ytile'] = ConfigInt(min_value=1)
        self.config['sym'] = ConfigBool(True)

    def on_start(self):
        # send first window
        self.make_window()

    def on_set_config(self):
        # send more windows if config changes
        self.make_window()


class Hann(WindowBase):
    """Hann window.

    ===========  ====  ====
    Config
    ===========  ====  ====
    ``xtile``    int   Horizontal tile size.
    ``ytile``    int   Vertical tile size.
    ``sym``      bool  When True (default), generates a symmetric window.
    ===========  ====  ====

    """
    def make_window(self):
        self.update_config()
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        sym = self.config['sym']
        self.send('output', HannCore(x_tile=x_tile, y_tile=y_tile, sym=sym))


class Hamming(WindowBase):
    """Hamming window.

    ===========  ====  ====
    Config
    ===========  ====  ====
    ``xtile``    int   Horizontal tile size.
    ``ytile``    int   Vertical tile size.
    ``sym``      bool  When True (default), generates a symmetric window.
    ===========  ====  ====

    """
    def make_window(self):
        self.update_config()
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        sym = self.config['sym']
        self.send('output', HammingCore(x_tile=x_tile, y_tile=y_tile, sym=sym))


class Blackman(WindowBase):
    """Blackman window.

    ===========  =====  ====
    Config
    ===========  =====  ====
    ``xtile``    int    Horizontal tile size.
    ``ytile``    int    Vertical tile size.
    ``sym``      bool   When True (default), generates a symmetric window.
    ``alpha``    float  Window control parameter.
    ===========  =====  ====

    """
    def initialise(self):
        super(Blackman, self).initialise()
        self.config['alpha'] = ConfigFloat(value=0.16)

    def make_window(self):
        self.update_config()
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        sym = self.config['sym']
        alpha = self.config['alpha']
        self.send('output', BlackmanCore(
            x_tile=x_tile, y_tile=y_tile, sym=sym, alpha=alpha))


class Kaiser(WindowBase):
    """Kaiser-Bessel window.

    See :py:func:`numpy:numpy.kaiser` for more detail. Note that NumPy
    and SciPy use a control parameter called ``beta``. This is ``alpha *
    pi``.

    ===========  =====  ====
    Config
    ===========  =====  ====
    ``xtile``    int    Horizontal tile size.
    ``ytile``    int    Vertical tile size.
    ``sym``      bool   When True (default), generates a symmetric window.
    ``alpha``    float  Window control parameter.
    ===========  =====  ====

    """
    def initialise(self):
        super(Kaiser, self).initialise()
        self.config['alpha'] = ConfigFloat(value=0.9)

    def make_window(self):
        self.update_config()
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        sym = self.config['sym']
        alpha = self.config['alpha']
        self.send('output', KaiserCore(
            x_tile=x_tile, y_tile=y_tile, sym=sym, alpha=alpha))


def Window2D(name, x_tile, y_tile, sym, function_1D, x_params={}, y_params={}):
    if x_tile == 1:
        x_win = numpy.array([1.0], dtype=numpy.float32)
    elif sym:
        x_win = function_1D(x_tile, **x_params)
    else:
        x_win = function_1D(x_tile + 1, **x_params)[:-1]
    if y_tile == 1:
        y_win = numpy.array([1.0], dtype=numpy.float32)
    elif sym:
        y_win = function_1D(y_tile, **y_params)
    else:
        y_win = function_1D(y_tile + 1, **y_params)[:-1]
    x_win = x_win.reshape((1, 1, -1, 1))
    y_win = y_win.reshape((1, -1, 1, 1))
    out_frame = Frame()
    out_frame.data = x_win * y_win
    out_frame.type = 'win'
    audit = out_frame.metadata.get('audit')
    audit += 'data = %sWindow()\n' % name
    audit += '    size: %d x %d\n' % (y_tile, x_tile)
    audit += '    symmetric: %s\n' % (str(sym))
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


def HannCore(x_tile=1, y_tile=1, sym=True):
    def Hann_1D(tile):
        result = numpy.ndarray([tile], dtype=numpy.float32)
        for i in range(tile):
            result[i] = 0.5 + (0.5 * math.cos(
                math.pi * float((i * 2) + tile - 1) / float(tile - 1)))
        return result

    return Window2D('Hann', x_tile, y_tile, sym, Hann_1D)


def HammingCore(x_tile=1, y_tile=1, sym=True):
    def Hamming_1D(tile):
        result = numpy.ndarray([tile], dtype=numpy.float32)
        for i in range(tile):
            result[i] = 0.53836 + (0.46164 * math.cos(
                math.pi * float((i * 2) + tile - 1) / float(tile - 1)))
        return result

    return Window2D('Hamming', x_tile, y_tile, sym, Hamming_1D)


def BlackmanCore(x_tile=1, y_tile=1, sym=True, alpha=0.16):
    def Blackman_1D(tile, alpha):
        result = numpy.ndarray([tile], dtype=numpy.float32)
        a0 = (1.0 - alpha) / 2.0
        a1 = -1.0 / 2.0
        a2 = alpha / 2.0
        for i in range(tile):
            f = math.pi * float(i * 2) / float(tile - 1)
            result[i] = a0 + (a1 * math.cos(f)) + (a2 * math.cos(2.0 * f))
        return result

    return Window2D('Blackman', x_tile, y_tile, sym, Blackman_1D,
                    x_params={'alpha' : alpha}, y_params={'alpha' : alpha})


def KaiserCore(x_tile=1, y_tile=1, sym=True, alpha=0.9):
    def Kaiser_1D(tile, alpha=0.9):
        return numpy.kaiser(tile, alpha * math.pi)

    return Window2D('Kaiser', x_tile, y_tile, sym, Kaiser_1D,
                    x_params={'alpha' : alpha}, y_params={'alpha' : alpha})


def _Hann_1D(tile, alpha):
    return numpy.hanning(tile)

def _Hamming_1D(tile, alpha):
    return numpy.hamming(tile)

def _Blackman_1D(tile, alpha):
    return numpy.blackman(tile)

def _Kaiser_1D(tile, alpha):
    return numpy.kaiser(tile, alpha * math.pi)

class Window(Component):
    """General 2-D window.

    The ``function`` parameter selects one of several widely used 1-D
    window functions. The ``sym`` parameter makes the window symmetrical
    or not. Note that a symmetrical window with an even size does not
    have a central value of unity.

    ``alpha`` is the control parameter for the ``Kaiser`` window. See
    :py:func:`numpy:numpy.kaiser` for more detail. Note that NumPy and
    SciPy use a control parameter called ``beta``, which is ``alpha *
    pi``.

    The ``combine2D`` parameter selects how the horizontal and vertical
    windows are combined to make a 2-D window. (If either dimension has
    size one it has no effect.) The option names refer to the shape of
    the contours if you plotted the window. ``square`` means the two
    windows are simply multiplied together. ``round`` means the window
    value depends on the normalised distance from the centre of the
    window, with points further than 0.5 set to zero. ``round2`` is an
    alternative that is normalised to the diagonal, so no points are
    further than 0.5.

    =============  =====  ====
    Config
    =============  =====  ====
    ``xtile``      int    Horizontal tile size.
    ``ytile``      int    Vertical tile size.
    ``sym``        bool   When True (default), generates a symmetric window.
    ``combine2D``  str    How to combine 1-D windows to make 2-D window. Can be ``square``, ``round`` or ``round2``.
    ``function``   str    Choose the window function. Possible values: {}
    ``alpha``      float  Window control parameter.
    =============  =====  ====

    """
    inputs = []
    with_outframe_pool = False

    functions = OrderedDict((
        # name        function       has alpha
        ('Hann',     (_Hann_1D,      False)),
        ('Hamming',  (_Hamming_1D,   False)),
        ('Blackman', (_Blackman_1D,  True)),
        ('Kaiser',   (_Kaiser_1D,    True)),
        ))
    __doc__ = __doc__.format(', '.join(["``'" + x + "'``" for x in functions]))

    def initialise(self):
        self.config['xtile'] = ConfigInt(min_value=1)
        self.config['ytile'] = ConfigInt(min_value=1)
        self.config['sym'] = ConfigBool(True)
        self.config['combine2D'] = ConfigEnum(choices=('square', 'round', 'round2'))
        self.config['function'] = ConfigEnum(choices=self.functions.keys())
        self.config['alpha'] = ConfigFloat()

    def on_start(self):
        # send first window
        self.make_window()

    def on_set_config(self):
        # send more windows if config changes
        self.make_window()

    def make_window(self):
        self.update_config()
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        sym = self.config['sym']
        combine2D = self.config['combine2D']
        function = self.config['function']
        alpha = self.config['alpha']
        function_1D, has_alpha = self.functions[function]
        if combine2D == 'square' or x_tile == 1 or y_tile == 1:
            if x_tile == 1:
                x_win = numpy.array([1.0])
            elif sym:
                x_win = function_1D(x_tile, alpha)
            else:
                x_win = function_1D(x_tile + 1, alpha)[:-1]
            if y_tile == 1:
                y_win = numpy.array([1.0])
            elif sym:
                y_win = function_1D(y_tile, alpha)
            else:
                y_win = function_1D(y_tile + 1, alpha)[:-1]
            x_win = x_win.reshape((1, 1, -1, 1))
            y_win = y_win.reshape((1, -1, 1, 1))
            window = x_win * y_win
        else:
            xc, yc = x_tile // 2, y_tile // 2
            if sym:
                xc, yc = xc - 0.5, yc - 0.5
            func_win = numpy.zeros((2049,), dtype=pt_float)
            func_win[0:1025] = function_1D(2049, alpha)[1024:]
            window = numpy.empty((1, y_tile, x_tile, 1), dtype=pt_float)
            for y in range(y_tile):
                for x in range(x_tile):
                    window[0, y, x, 0] = math.sqrt((((x - xc) / x_tile) ** 2) +
                                                   (((y - yc) / y_tile) ** 2))
            if combine2D == 'round2':
                window /= math.sqrt(2.0)
            window = numpy.interp(
                window, numpy.linspace(0, 1.0, func_win.shape[0]), func_win)
        out_frame = Frame()
        out_frame.data = window.astype(pt_float)
        out_frame.type = 'win'
        audit = out_frame.metadata.get('audit')
        audit += 'data = %sWindow()\n' % function
        audit += '    size: %d x %d\n' % (y_tile, x_tile)
        audit += '    symmetric: %s\n' % str(sym)
        if has_alpha:
            audit += '    alpha: %g\n' % alpha
        out_frame.metadata.set('audit', audit)
        self.send('output', out_frame)


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
    outputs = ['window', 'inv_window']      #:
    with_outframe_pool = False

    def initialise(self):
        self.config['xtile'] = ConfigInt(min_value=1)
        self.config['ytile'] = ConfigInt(min_value=1)
        self.config['xoff'] = ConfigInt(min_value=1)
        self.config['yoff'] = ConfigInt(min_value=1)
        self.config['fade'] = ConfigEnum(choices=('switch', 'linear', 'minsnr'))
        self.in_frame = None

    def on_set_config(self):
        # send more windows if config changes
        if self.in_frame:
            self.make_window()

    def process_frame(self):
        self.in_frame = self.input_buffer['input'].get()
        self.send('window', self.in_frame)
        self.make_window()

    def make_window(self):
        self.update_config()
        x_tile = self.config['xtile']
        y_tile = self.config['ytile']
        x_off = self.config['xoff']
        y_off = self.config['yoff']
        fade = self.config['fade']
        # adjust config to suit actual window
        in_data = self.in_frame.as_numpy(dtype=numpy.float32)
        if in_data.shape[1] != y_tile:
            y_off = y_off * in_data.shape[1] // y_tile
            y_tile = in_data.shape[1]
        if in_data.shape[2] != x_tile:
            x_off = x_off * in_data.shape[2] // x_tile
            x_tile = in_data.shape[2]
        out_frame = Frame()
        out_frame.initialise(self.in_frame)
        audit = out_frame.metadata.get('audit')
        audit += 'data = InverseWindow(data)\n'
        audit += '    size: %d x %d, offset: %d x %d\n' % (
            y_tile, x_tile, y_off, x_off)
        audit += '    fade: %s\n' % fade
        out_frame.metadata.set('audit', audit)

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
        self.send('inv_window', out_frame)
