#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2018-19  Pyctools contributors
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


def ImageResizerX(config={}, **kwds):
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
    cfg = {'aperture': 16}
    cfg.update(kwds)
    cfg.update(config)
    return Compound(
        filgen = FilterGenerator(),
        resize = Resize(),
        config = cfg,
        config_map = {
            'filgen': (('up', 'xup'), ('down', 'xdown'),
                       ('aperture', 'xaperture')),
            'resize': (('up', 'xup'), ('down', 'xdown')),
            },
        linkages = {
            ('self',   'input')  : ('resize', 'input'),
            ('filgen', 'output') : ('resize', 'filter'),
            ('resize', 'output') : ('self',   'output'),
            }
        )


def ImageResizerY(config={}, **kwds):
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
    cfg = {'aperture': 16}
    cfg.update(kwds)
    cfg.update(config)
    return Compound(
        filgen = FilterGenerator(),
        resize = Resize(),
        config = cfg,
        config_map = {
            'filgen': (('up', 'yup'), ('down', 'ydown'),
                       ('aperture', 'yaperture')),
            'resize': (('up', 'yup'), ('down', 'ydown')),
            },
        linkages = {
            ('self',   'input')  : ('resize', 'input'),
            ('filgen', 'output') : ('resize', 'filter'),
            ('resize', 'output') : ('self',   'output'),
            }
        )


def ImageResizer2D(config={}, **kwds):
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
    cfg = {'xaperture': 16, 'yaperture': 16}
    cfg.update(kwds)
    cfg.update(config)
    return Compound(
        xfilgen = FilterGenerator(),
        yfilgen = FilterGenerator(),
        xresize = Resize(),
        yresize = Resize(),
        config = cfg,
        config_map = {
            'xfilgen': (('xup', 'xup'), ('xdown', 'xdown'),
                        ('xaperture', 'xaperture')),
            'yfilgen': (('yup', 'yup'), ('ydown', 'ydown'),
                        ('yaperture', 'yaperture')),
            'xresize': (('xup', 'xup'), ('xdown', 'xdown')),
            'yresize': (('yup', 'yup'), ('ydown', 'ydown')),
            },
        linkages = {
            ('self',    'input')  : ('yresize', 'input'),
            ('yfilgen', 'output') : ('yresize', 'filter'),
            ('yresize', 'output') : ('xresize', 'input'),
            ('xfilgen', 'output') : ('xresize', 'filter'),
            ('xresize', 'output') : ('self',    'output'),
            }
        )
