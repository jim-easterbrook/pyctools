#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2019-22  Pyctools contributors
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

__all__ = ['Reorient']
__docformat__ = 'restructuredtext en'

import numpy

from pyctools.core.config import ConfigEnum
from pyctools.core.base import Transformer


class Reorient(Transformer):
    """Rotate and/or reflect an image.

    This can be used to convert photographs to the normal viewing
    orientation, rather than relying on the metadata orientation flag.

    The ``orientation`` parameter sets the current orientation of the
    image. If it's ``auto`` the value is taken from the image metadata.

    ===============  ===  ====
    Config
    ===============  ===  ====
    ``orientation``  str  The current orientation. Possible values: {}.
    ===============  ===  ====

    """

    orientations = {
        'auto': 0,
        'normal': 1,             'rotate -90': 6,
        'rotate +90': 8,         'rotate 180': 3,
        'reflect left-right': 2, 'reflect top-bottom': 4,
        'reflect tr-bl': 5,      'reflect tl-br': 7
        }

    __doc__ = __doc__.format(', '.join(
        ['``{}``'.format(x) for x in orientations]))

    def initialise(self):
        self.config['orientation'] = ConfigEnum(choices=self.orientations)

    def orient_text(self, int_val):
        for key, value in self.orientations.items():
            if value == int_val:
                return key
        return 'unknown'

    def transform(self, in_frame, out_frame):
        self.update_config()
        # get orientation
        orientation = self.orientations[self.config['orientation']]
        if not orientation:
            orientation = 1
            for tag, data in (
                    ('Exif.Image.Orientation', out_frame.metadata.exif_data),
                    ('Xmp.tiff.Orientation', out_frame.metadata.xmp_data)):
                if tag in data:
                    orientation = int(data[tag])
                    break
        # clear metadata orientation flag
        for tag, data in (
                ('Exif.Image.Orientation', out_frame.metadata.exif_data),
                ('Xmp.tiff.Orientation', out_frame.metadata.xmp_data)):
            if tag in data:
                del data[tag]
        # do transformation
        orient_bits = orientation - 1
        if orient_bits:
            data = out_frame.as_numpy()
            if orient_bits & 0b100:
                # transpose horizontal & vertical
                data = numpy.swapaxes(data, 0, 1)
            flip_v, flip_h = False, False
            if orient_bits & 0b010:
                # rotate 180
                flip_h = not flip_h
                flip_v = not flip_v
            if orient_bits & 0b001:
                # reflect left-right
                flip_h = not flip_h
            if flip_v:
                data = numpy.flipud(data)
            if flip_h:
                data = numpy.fliplr(data)
            out_frame.data = data
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = Reorient(data)\n'
        audit += '    from "{}"\n'.format(self.orient_text(orientation))
        audit += self.config.audit_string()
        out_frame.metadata.set('audit', audit)
        return True
