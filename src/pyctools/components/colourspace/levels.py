#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2019  Pyctools contributors
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

__all__ = ['ComputerToStudio', 'StudioToComputer']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigFloat
from pyctools.core.base import Component
from pyctools.core.types import pt_float


class ComputerToStudio(Component):
    """Convert "computer" range to "studio".

    Most image file formats use a black to white range of 0..255. Video
    conforming to `Rec. 601`_ uses 16..235. This component converts from
    0..255 to 16..235. This is essential before writing video to some
    file formats.

    The ``black`` config item over-rides the output black level. The
    ``white`` config item over-rides the output white level.

    .. _Rec. 601: https://en.wikipedia.org/wiki/Rec._601

    """

    def initialise(self):
        self.config['black'] = ConfigFloat(default=16.0)
        self.config['white'] = ConfigFloat(default=235.0)

    def transform(self, in_frame, out_frame):
        self.update_config()
        black = self.config['black']
        white = self.config['white']
        gain = pt_float((white - black) / 255.0)
        sit = pt_float(black)
        data = in_frame.as_numpy(dtype=pt_float)
        out_frame.data = (data * gain) + sit
        audit = out_frame.metadata.get('audit')
        audit += 'data = ComputerToStudio(data)\n'
        audit += '    0-255 -> {}-{}'.format(black, white)
        out_frame.metadata.set('audit', audit)
        return True


class StudioToComputer(Component):
    """Convert "studio" range to "computer".

    Most image file formats use a black to white range of 0..255. Video
    conforming to `Rec. 601`_ uses 16..235. This component converts from
    16..235 to 0..255. This is essential after reading video from some
    file formats.

    The ``black`` config item over-rides the input black level. The
    ``white`` config item over-rides the input white level.

    .. _Rec. 601: https://en.wikipedia.org/wiki/Rec._601

    """

    def initialise(self):
        self.config['black'] = ConfigFloat(default=16.0)
        self.config['white'] = ConfigFloat(default=235.0)

    def transform(self, in_frame, out_frame):
        self.update_config()
        black = self.config['black']
        white = self.config['white']
        gain = pt_float(255.0 / (white - black))
        sit = pt_float(black)
        data = in_frame.as_numpy(dtype=pt_float)
        out_frame.data = (data - sit) * gain
        audit = out_frame.metadata.get('audit')
        audit += 'data = StudioToComputer(data)\n'
        audit += '    {}-{} -> 0-255'.format(black, white)
        out_frame.metadata.set('audit', audit)
        return True
