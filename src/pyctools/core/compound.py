#!/usr/bin/env python
#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014  Jim Easterbrook  jim@jim-easterbrook.me.uk
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

"""Compound component."""

__docformat__ = 'restructuredtext en'

from .config import ConfigGrandParent

class Compound(object):
    """Encapsulates several components into one. Closely modeled on
    `Kamaelia's 'Graphline' component
    <http://www.kamaelia.org/Components/pydoc/Kamaelia.Chassis.Graphline.html>`_.
    Components are linked within the compound and to the outside world
    according to the `linkages` parameter.

    For example, you could create an image resizer by connecting a
    :py:class:`~pyctools.components.interp.filtergenerator.FilterGenerator`
    to a :py:class:`~pyctools.components.interp.resize.Resize` as
    follows::

        def ImageResizer(x_up=1, x_down=1, y_up=1, y_down=1):
            filgen = FilterGenerator()
            resize = Resize()
            fg_cfg = filgen.get_config()
            rs_cfg = resize.get_config()
            if x_up != 1 or x_down != 1:
                fg_cfg['xup'] = x_up
                fg_cfg['xdown'] = x_down
                fg_cfg['xaperture'] = 16
                rs_cfg['xup'] = x_up
                rs_cfg['xdown'] = x_down
            if y_up != 1 or y_down != 1:
                fg_cfg['yup'] = y_up
                fg_cfg['ydown'] = y_down
                fg_cfg['yaperture'] = 16
                rs_cfg['yup'] = y_up
                rs_cfg['ydown'] = y_down
            filgen.set_config(fg_cfg)
            resize.set_config(rs_cfg)
            return Compound(
                filgen = filgen,
                resize = resize,
                linkages = {
                    ('self',   'input')  : ('resize', 'input'),
                    ('filgen', 'output') : ('resize', 'filter'),
                    ('resize', 'output') : ('self',   'output'),
                    }
                )

    Note the use of ``'self'`` in the `linkages` parameter to denote
    the compound object's own inputs and outputs. These are connected
    directly to the child components with no runtime overhead. There
    is no performance disadvantage from using compound objects.

    The child components' configuration objects are gathered into one
    :py:class:`~.config.ConfigGrandParent`. The child names are used
    to index the :py:class:`~.config.ConfigGrandParent`'s value dict.
    For example, if you wanted to change the filter aperture of the
    image resizer shown above (even while it's running!) you might do
    this::

        cfg = image_resizer.get_config()
        cfg['filgen']['xaperture'] = 8
        image_resizer.set_config(cfg)

    This allows compound components to be nested to any depth whilst
    still making their configuration available at the top level.

    :keyword Component name: Add ``Component`` to the network as
        ``name``. Can be repeated with different values of ``name``.

    :keyword dict linkages: A mapping from component outputs to
        component inputs.

    """
    def __init__(self, **kw):
        super(Compound, self).__init__()
        self.inputs = []
        self.outputs = []
        # get child components
        self._compound_children = {}
        for key in kw:
            if key == 'linkages':
                continue
            self._compound_children[key] = kw[key]
        # set up linkages
        self._compound_outputs = {}
        for source in kw['linkages']:
            src, outbox = source
            dest, inbox = kw['linkages'][source]
            if src == 'self':
                setattr(self, inbox,
                        getattr(self._compound_children[dest], inbox))
                self.inputs.append(outbox)
            elif dest == 'self':
                self._compound_outputs[inbox] = (src, outbox)
                self.outputs.append(inbox)
            else:
                self._compound_children[src].bind(
                    outbox, self._compound_children[dest], inbox)

    def bind(self, source, dest, destmeth):
        src, outbox = self._compound_outputs[source]
        self._compound_children[src].bind(outbox, dest, destmeth)

    def get_config(self):
        config = ConfigGrandParent()
        for name, child in self._compound_children.items():
            child_config = child.get_config()
            config[name] = child_config
        return config

    def set_config(self, config):
        for name, child_config in config.value.items():
            self._compound_children[name].set_config(child_config)

    def go(self):
        self.start()
        return self

    def start(self):
        for child in self._compound_children.values():
            child.start()

    def stop(self):
        for child in self._compound_children.values():
            child.stop()

    def join(self):
        for child in self._compound_children.values():
            child.join()
