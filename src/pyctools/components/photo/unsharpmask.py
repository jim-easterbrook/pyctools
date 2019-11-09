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

__all__ = ['UnsharpMask']
__docformat__ = 'restructuredtext en'

import cv2
import numpy

from pyctools.components.interp.gaussianfilter import GaussianFilterCore
from pyctools.components.interp.resizecore import resize_frame
from pyctools.core.config import ConfigBool, ConfigFloat
from pyctools.core.base import Transformer
from pyctools.core.types import pt_float


class UnsharpMask(Transformer):
    """Enhance image detail using an unsharp mask.

    The `unsharp mask`_ is computed by subtracting a `Gaussian blurred`_
    image from the original image. Low amplitude detail can be removed
    before the mask is added back to the image to sharpen it. This can
    reduce the increase in noise when lots of sharpening is applied.

    The ``amount`` parameter specifies how much sharpening to apply. It
    is a real number rather than the percentage used in some software.
    The ``radius`` parameter sets the standard deviation of the Gaussian
    blurring filter.

    To avoid discontinuities in the mask the threshold is used in a
    "coring" function. Detail lower than the threshold is ignored,
    detail above the threshold is reduced by the threshold value.

    Another option to reduce noise is ``denoise``. This uses a 5x5
    median filter as part of the mask computation.

    =============  =====  ====
    Config
    =============  =====  ====
    ``amount``     float  Amount of sharpening to apply.
    ``radius``     float  Size of blurring function.
    ``threshold``  float  Don't sharpen low amplitude detail.
    ``denoise``    bool   Median filter the detail to suppress noise.
    =============  =====  ====

    .. _Gaussian blurred: https://en.wikipedia.org/wiki/Gaussian_blur
    .. _unsharp mask:     https://en.wikipedia.org/wiki/Unsharp_masking

    """

    def initialise(self):
        self.config['amount'] = ConfigFloat(value=1.0, decimals=2)
        self.config['radius'] = ConfigFloat(value=2.0, decimals=1)
        self.config['threshold'] = ConfigFloat(value=0.0, decimals=1)
        self.config['denoise'] = ConfigBool()

    def transform(self, in_frame, out_frame):
        self.update_config()
        amount = self.config['amount']
        radius = self.config['radius']
        threshold = self.config['threshold']
        denoise = self.config['denoise']
        data = in_frame.as_numpy(dtype=pt_float)
        # median filter image before computing mask
        if denoise:
            mask = cv2.medianBlur(data, 5)
        else:
            mask = data
        # blur data with Gaussian and subtract to make mask
        h_filter = GaussianFilterCore(x_sigma=radius).as_numpy(dtype=pt_float)
        v_filter = GaussianFilterCore(y_sigma=radius).as_numpy(dtype=pt_float)
        mask = mask - resize_frame(resize_frame(
            mask, h_filter, 1, 1, 1, 1), v_filter, 1, 1, 1, 1)
        # core out mask values below threshold
        if threshold > 0.0:
            mask_p = mask - pt_float(threshold)
            mask_p *= mask_p > pt_float(0)
            mask_n = mask + pt_float(threshold)
            mask_n *= mask_n < pt_float(0)
            mask = mask_p + mask_n
        # add some mask back to image
        out_frame.data = data + (mask * amount)
        # add audit
        audit = out_frame.metadata.get('audit')
        audit += 'data = UnsharpMask(data)\n'
        audit += self.config.audit_string()
        out_frame.metadata.set('audit', audit)
        return True
