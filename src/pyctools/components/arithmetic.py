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

__all__ = ['Arithmetic', 'Arithmetic2', 'Script0', 'Script']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigEnum, ConfigInt, ConfigStr
from pyctools.core.base import Component, Transformer
from pyctools.core.types import pt_float, pt_complex


class Arithmetic(Transformer):
    """Do simple arithmetic.

    Applies a user supplied arithmetical expression to every pixel in
    each frame. To set the expression, set the component's ``func``
    config to a suitable string expression. The input data should appear
    in your expression as the word ``data``.

    For example, to convert video levels from the range ``16..235`` to
    ``64..204`` you could do this::

        setlevel = Arithmetic(
            func='((data - pt_float(16.0)) * pt_float(140.0 / 219.0)) + pt_float(64.0)')
        ...
        pipeline(..., setlevel, ...)

    Note the liberal use of :py:data:`~pyctools.core.types.pt_float` to
    coerce numbers to the Pyctools default floating point type
    (:py:class:`numpy:numpy.float32`). NumPy will otherwise convert
    Python :py:class:`float` to :py:class:`numpy:numpy.float64`.

    """

    def initialise(self):
        self.config['func'] = ConfigStr(value='data')

    def transform(self, in_frame, out_frame):
        self.update_config()
        func = self.config['func']
        data = in_frame.as_numpy()
        out_frame.data = eval(func)
        out_frame.set_audit(self, 'data = {}\n'.format(func))
        return True


class Arithmetic2(Component):
    """Do simple arithmetic with two inputs.

    Similar to :py:class:`Arithmetic`, but has two inputs. For example,
    to subtract the second input from the first you could do::

        subtracter = Arithmetic2(func='data1 - data2')

    """

    inputs = ['input1', 'input2']   #:

    def initialise(self):
        self.config['func'] = ConfigStr(value='data1 + data2')

    def process_frame(self):
        in_frame1 = self.input_buffer['input1'].get()
        in_frame2 = self.input_buffer['input2'].get()
        out_frame = self.outframe_pool['output'].get()
        self.update_config()
        func = self.config['func']
        data1 = in_frame1.as_numpy()
        data2 = in_frame2.as_numpy()
        out_frame.initialise(in_frame1)
        out_frame.data = eval(func)
        # audit
        out_frame.merge_audit({'data1': in_frame1, 'data2': in_frame2})
        out_frame.set_audit(self, 'data = {}\n'.format(func))
        self.send('output', out_frame)


class Script0(Component):
    """Generate image data with a short script.

    Runs a user supplied Python script to generate each frame. To set
    the script, set the component's ``script`` config to a suitable
    string expression, using semicolons to separate lines. The output
    data should appear in your expression as the word ``data``.

    For example, to generate moving vertical stripes you could do this::

        stripes = Script(
            script='x=numpy.mgrid[0:480];x=(x+out_frame.frame_no)%26;data=numpy.where(x.reshape(1,-1,1)>=13,numpy.full((360,480,3),220),40)',
            zlen=26, looping='repeat')
        ...
        pipeline(stripes, ...)

    """

    inputs = []

    def initialise(self):
        self.config['script'] = ConfigStr()
        self.config['zlen'] = ConfigInt(value=100, min_value=1)
        self.config['looping'] = ConfigEnum(choices=('off', 'repeat'))
        self.frame_no = 0

    def process_frame(self):
        self.update_config()
        script = self.config['script']
        zlen = self.config['zlen']
        if self.frame_no >= zlen and self.config['looping'] == 'off':
            self.stop()
            return
        out_frame = self.outframe_pool['output'].get()
        out_frame.frame_no = self.frame_no
        self.frame_no += 1
        locals_ = dict(locals())
        exec(script, globals(), locals_)
        out_frame.data = locals_['data']
        out_frame.set_audit(
            self, 'script:' + '\n    '.join(script.split(';')) + '\n')
        if out_frame.data.shape[-1] == 1:
            out_frame.type = 'Y'
        elif out_frame.data.shape[-1] == 3:
            out_frame.type = 'RGB'
        elif out_frame.data.shape[-1] == 2:
            out_frame.type = 'UV'
        else:
            out_frame.type = '???'
        self.send('output', out_frame)


class Script(Transformer):
    """Run a short script on image data.

    Applies a user supplied Python script to each frame. To set the
    script, set the component's ``script`` config to a suitable string
    expression, using semicolons to separate lines. The input data
    should appear in your expression as the word ``data``. Do not modify
    the data in place, but make a copy with the result of your script.

    For example, to paste a block of red into an image you could do this::

        patch = Script(
            script='data=data.copy();data[100:115,100:120,:]=[255,0,0]')
        ...
        pipeline(..., patch, ...)

    """

    def initialise(self):
        self.config['script'] = ConfigStr()

    def transform(self, in_frame, out_frame):
        self.update_config()
        script = self.config['script']
        data = in_frame.as_numpy()
        locals_ = dict(locals())
        exec(script, globals(), locals_)
        out_frame.data = locals_['data']
        out_frame.set_audit(
            self, 'script:' + '\n    '.join(script.split(';')) + '\n')
        return True
