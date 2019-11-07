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

__all__ = ['ImageFileReaderPIL', 'ImageFileWriterPIL']
__docformat__ = 'restructuredtext en'

import io
import os

import PIL.Image

from pyctools.core.config import ConfigBool, ConfigPath, ConfigStr
from pyctools.core.base import Component, Transformer
from pyctools.core.frame import Frame, Metadata

class ImageFileReaderPIL(Component):
    """Read a still image file using Python Imaging Library.

    Reads an image file using :py:func:`PIL.Image.open`. This function
    cannot handle 16-bit data, so you may prefer to use
    :py:class:`~pyctools.components.io.imagefilecv.ImageFileReaderCV`
    instead.

    ========  ===  ====
    Config
    ========  ===  ====
    ``path``  str  Path name of file to be read.
    ========  ===  ====

    """
    inputs = []
    with_outframe_pool = False

    def initialise(self):
        self.config['path'] = ConfigPath()

    def on_start(self):
        # read file
        self.update_config()
        path = self.config['path']
        out_frame = Frame()
        image = PIL.Image.open(path)
        image.load()
        # send output frame
        out_frame.data = image
        out_frame.type = image.mode
        out_frame.frame_no = 0
        out_frame.metadata.from_file(path)
        audit = out_frame.metadata.get('audit')
        audit += 'data = {}\n'.format(os.path.basename(path))
        audit += self.config.audit_string()
        out_frame.metadata.set('audit', audit)
        self.send('output', out_frame)
        # shut down pipeline
        self.stop()


class ImageFileWriterPIL(Transformer):
    """Write a still image file using Python Imaging Library.

    This component saves the first frame it receives to file using
    :py:meth:`PIL.Image.Image.save`.

    See the `PIL documentation
    <http://pillow.readthedocs.io/en/latest/handbook/image-file-formats.html>`_
    for details of the available formats and options.

    The ``options`` configuration should be a comma separated list of
    colon separated names and values, for example a JPEG file might have
    these options: ``'quality': 95, 'progressive': True``.

    The ``set_thumbnail`` option allows you to store a DCF standard 160
    x 120 (or 120 x 160) thumbnail in the Exif metadata.

    PIL cannot write 16-bit data, so you may prefer to use
    :py:class:`~pyctools.components.io.imagefilecv.ImageFileWriterCV`
    instead.

    =================  ====  ====
    Config
    =================  ====  ====
    ``path``           str   Path name of file to be created.
    ``format``         str   Over-ride the file format. This is normally derived from the ``path`` extension.
    ``options``        str   A string of :py:meth:`PIL.Image.Image.save` options.
    ``set_thumbnail``  bool  Create and add an Exif thumbnail.
    =================  ====  ====

    """
    def initialise(self):
        self.done = False
        self.config['path'] = ConfigPath(exists=False)
        self.config['format'] = ConfigStr()
        self.config['options'] = ConfigStr()
        self.config['set_thumbnail'] = ConfigBool(value=False)

    def transform(self, in_frame, out_frame):
        if self.done:
            return True
        self.update_config()
        path = self.config['path']
        fmt = self.config['format'] or None
        options = eval('{' + self.config['options'] + '}')
        # save image
        image = in_frame.as_PIL()
        image.save(path, format=fmt, **options)
        # save metadata
        md = Metadata().copy(in_frame.metadata)
        audit = md.get('audit')
        audit += '{} = data\n'.format(os.path.basename(path))
        audit += self.config.audit_string()
        md.set('audit', audit)
        if self.config['set_thumbnail']:
            w, h = image.size
            if w >= h:
                w, h = 160, 120
            else:
                w, h = 120, 160
            image.thumbnail((w, h), PIL.Image.ANTIALIAS)
            wt, ht = image.size
            if (wt, ht) != (w, h):
                # pad with black
                padded = PIL.Image.new(image.mode, (w, h))
                padded.paste(image, ((w - wt) // 2, (h - ht) // 2))
                image = padded
            buf = io.BytesIO()
            image.save(buf, format='JPEG', params={'quality': 95})
            md.to_file(path, thumbnail=buf.getbuffer())
        else:
            md.to_file(path)
        self.done = True
        return True
