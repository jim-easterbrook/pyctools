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

__all__ = ['NonlocalMeansDenoise']
__docformat__ = 'restructuredtext en'

import cv2
import numpy

from pyctools.core.base import Transformer
from pyctools.core.config import ConfigFloat, ConfigInt


class NonlocalMeansDenoise(Transformer):
    """Non-local means image denoising.

    """

    def initialise(self):
        self.config['templateWindowSize'] = ConfigInt(value=7)
        self.config['searchWindowSize'] = ConfigInt(value=21)
        self.config['h_Y'] = ConfigFloat(value=3.0)
        self.config['h_UV'] = ConfigFloat(value=10.0)

    def transform(self, in_frame, out_frame):
        self.update_config()
        templateWindowSize = self.config['templateWindowSize']
        searchWindowSize = self.config['searchWindowSize']
        h_Y = self.config['h_Y']
        h_UV = self.config['h_UV']
        # get data
        data = in_frame.as_numpy(dtype=numpy.uint8)
        comps = data.shape[-1]
        if comps == 1:
            out_frame.data = cv2.fastNlMeansDenoising(
                data, h=h_Y,
                templateWindowSize=templateWindowSize,
                searchWindowSize=searchWindowSize)
        elif comps == 3:
            out_frame.data = cv2.fastNlMeansDenoisingColored(
                data, h=h_Y, hColor=h_UV,
                templateWindowSize=templateWindowSize,
                searchWindowSize=searchWindowSize)
        else:
            self.logger.critical('Cannot denoise %s images with %d components',
                                 in_frame.type, comps)
            return False
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = NonlocalMeansDenoise(data)\n'
        audit += '    templateWindowSize: {}\n'.format(templateWindowSize)
        audit += '    searchWindowSize: {}\n'.format(searchWindowSize)
        audit += '    h_Y: {}\n'.format(h_Y)
        if comps == 3:
            audit += '    h_UV: {}\n'.format(h_UV)
        out_frame.metadata.set('audit', audit)
        return True
