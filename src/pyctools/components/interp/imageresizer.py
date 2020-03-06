#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2018-20  Pyctools contributors
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

__all__ = ['ImageResizerX', 'ImageResizerY', 'ImageResizer2D']
__docformat__ = 'restructuredtext en'

from pyctools.components.interp.filtergenerator import FilterGenerator
from pyctools.components.interp.resize import Resize
from pyctools.core.compound import Compound


class ImageResizerX(Compound):
    """Horizontal image resizer component.

    Uses a :py:class:`~pyctools.core.compound.Compound` component to
    encapsulate :py:class:`~.resize.Resize` and
    :py:class:`~.filtergenerator.FilterGenerator` components.

    Config:

    ============  ===  ====
    ``up``        int  Up-conversion factor.
    ``down``      int  Down-conversion factor.
    ``aperture``  int  Filter aperture.
    ============  ===  ====

    """
    def __init__(self, config={}, **kwds):
        cfg = {'aperture': 16}
        cfg.update(kwds)
        cfg.update(config)
        super(ImageResizerX, self).__init__(
            filgen = FilterGenerator(),
            resize = Resize(),
            config = cfg,
            config_map = {
                'up'               : ('filgen.xup',   'resize.xup'),
                'down'             : ('filgen.xdown', 'resize.xdown'),
                'aperture'         : ('filgen.xaperture',),
                'outframe_pool_len': ('resize.outframe_pool_len',),
                },
            linkages = {
                ('self',   'input')  : ('resize', 'input'),
                ('filgen', 'output') : ('resize', 'filter'),
                ('resize', 'output') : ('self',   'output'),
                }
            )


class ImageResizerY(Compound):
    """Vertical image resizer component.

    Uses a :py:class:`~pyctools.core.compound.Compound` component to
    encapsulate :py:class:`~.resize.Resize` and
    :py:class:`~.filtergenerator.FilterGenerator` components.

    Config:

    ============  ===  ====
    ``up``        int  Up-conversion factor.
    ``down``      int  Down-conversion factor.
    ``aperture``  int  Filter aperture.
    ============  ===  ====

    """
    def __init__(self, config={}, **kwds):
        cfg = {'aperture': 16}
        cfg.update(kwds)
        cfg.update(config)
        super(ImageResizerY, self).__init__(
            filgen = FilterGenerator(),
            resize = Resize(),
            config = cfg,
            config_map = {
                'up'               : ('filgen.yup',   'resize.yup'),
                'down'             : ('filgen.ydown', 'resize.ydown'),
                'aperture'         : ('filgen.yaperture',),
                'outframe_pool_len': ('xresize.outframe_pool_len',),
                },
            linkages = {
                ('self',   'input')  : ('resize', 'input'),
                ('filgen', 'output') : ('resize', 'filter'),
                ('resize', 'output') : ('self',   'output'),
                }
            )


class ImageResizer2D(Compound):
    """2-D image resizer component.

    Uses a :py:class:`~pyctools.core.compound.Compound` component to
    encapsulate two :py:class:`~.resize.Resize` and two
    :py:class:`~.filtergenerator.FilterGenerator` components.

    Using separate Resize components to filter each dimension is a lot
    quicker than using one Resize with a 2-D filter, particularly for
    large apertures.

    Config:

    =============  ===  ====
    ``xup``        int  Horizontal up-conversion factor.
    ``xdown``      int  Horizontal down-conversion factor.
    ``xaperture``  int  Horizontal filter aperture.
    ``yup``        int  Vertical up-conversion factor.
    ``ydown``      int  Vertical down-conversion factor.
    ``yaperture``  int  Vertical filter aperture.
    =============  ===  ====

    """
    def __init__(self, config={}, **kwds):
        cfg = {'xaperture': 16, 'yaperture': 16}
        cfg.update(kwds)
        cfg.update(config)
        super(ImageResizer2D, self).__init__(
            xfilgen = FilterGenerator(),
            yfilgen = FilterGenerator(),
            xresize = Resize(),
            yresize = Resize(),
            config = cfg,
            config_map = {
                'xup'              : ('xfilgen.xup',   'xresize.xup'),
                'xdown'            : ('xfilgen.xdown', 'xresize.xdown'),
                'yup'              : ('yfilgen.yup',   'yresize.yup'),
                'ydown'            : ('yfilgen.ydown', 'yresize.ydown'),
                'xaperture'        : ('xfilgen.xaperture',),
                'yaperture'        : ('yfilgen.yaperture',),
                'outframe_pool_len': ('xresize.outframe_pool_len',),
                },
            linkages = {
                ('self',    'input')  : ('yresize', 'input'),
                ('yfilgen', 'output') : ('yresize', 'filter'),
                ('yresize', 'output') : ('xresize', 'input'),
                ('xfilgen', 'output') : ('xresize', 'filter'),
                ('xresize', 'output') : ('self',    'output'),
                }
            )
