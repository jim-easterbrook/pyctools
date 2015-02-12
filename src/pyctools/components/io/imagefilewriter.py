# This file is part of pyctools http://github.com/jim-easterbrook/pyctools
# Copyright pyctools contributors
# Released under the GNU GPL3 licence

"""Save still image file.

This is a "pass through" component that can be inserted anywhere in a
pipeline. It saves the first frame it receives to file using
:py:meth:`PIL.Image.Image.save`.

"""

import PIL.Image

__all__ = ['ImageFileWriter']
__docformat__ = 'restructuredtext en'

from pyctools.core.config import ConfigPath
from pyctools.core.frame import Metadata
from pyctools.core.base import Transformer

class ImageFileWriter(Transformer):
    def initialise(self):
        self.done = False
        self.config['path'] = ConfigPath(exists=False)

    def transform(self, in_frame, out_frame):
        if self.done:
            return True
        self.update_config()
        path = self.config['path']
        image = in_frame.as_PIL()
        image.save(path)
        md = Metadata().copy(in_frame.metadata)
        audit = md.get('audit')
        audit += '%s = data\n' % path
        md.set('audit', audit)
        md.to_file(path)
        self.done = True
        return True
