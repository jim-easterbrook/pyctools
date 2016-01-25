#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-16  Pyctools contributors
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

"""Save still image file.

This component saves the first frame it receives to file using
:py:meth:`PIL.Image.Image.save`.

See the `PIL documentation
<http://pillow.readthedocs.org/en/latest/handbook/image-file-formats.html>`_
for details of the available formats and options.

The ``options`` configuration should be a comma separated list of colon
separated names and values, for example a JPEG file might have these
options: ``'quality': 95, 'progressive': True``.

===========  ===  ====
Config
===========  ===  ====
``path``     str  Path name of file to be created.
``format``   str  Over-ride the file format. This is normally derived from the ``path`` extension.
``options``  str  A string of :py:meth:`PIL.Image.Image.save` options.
===========  ===  ====

"""

import PIL.Image

__all__ = ['ImageFileWriter']
__docformat__ = 'restructuredtext en'

from pyctools.core.config import ConfigPath, ConfigStr
from pyctools.core.frame import Metadata
from pyctools.core.base import Transformer

class ImageFileWriter(Transformer):
    def initialise(self):
        self.done = False
        self.config['path'] = ConfigPath(exists=False)
        self.config['format'] = ConfigStr()
        self.config['options'] = ConfigStr()

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
        audit += '{} = data\n'.format(path)
        if fmt:
            audit += '    format: {}\n'.format(fmt)
        if options:
            audit += '    options: {}\n'.format(self.config['options'])
        md.set('audit', audit)
        md.to_file(path)
        self.done = True
        return True
