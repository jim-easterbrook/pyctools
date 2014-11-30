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

import logging

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
            xaperture = 1
            if x_up != 1 or x_down != 1:
                xaperture = 16
            yaperture = 1
            if y_up != 1 or y_down != 1:
                yaperture = 16
            filgen = FilterGenerator(
                xup=x_up, xdown=x_down, xaperture=xaperture,
                yup=y_up, ydown=y_down, yaperture=yaperture)
            resize = Resize(xup=x_up, xdown=x_down, yup=y_up, ydown=y_down)
            return Compound(
                filgen = filgen,
                resize = resize,
                linkages = {
                    ('self',   'input')  : ('resize', 'input'),
                    ('filgen', 'output') : ('resize', 'filter'),
                    ('resize', 'output') : ('self',   'output'),
                    }
                )

    Note the use of ``'self'`` in the :py:obj:`linkages` parameter to
    denote the compound object's own inputs and outputs. These are
    connected directly to the child components with no runtime
    overhead. There is no performance disadvantage from using compound
    objects.

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
        self.logger = logging.getLogger(self.__class__.__name__)
        self.inputs = []
        self.outputs = []
        # get child components
        self._compound_children = {}
        self._compound_linkages = {}
        for key, value in kw.items():
            if key == 'linkages':
                self._compound_linkages = value
            else:
                self._compound_children[key] = value
        # set up linkages
        self._compound_outputs = {}
        for (src, outbox), (dest, inbox) in self._compound_linkages.items():
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
        for name, child in self._compound_children.items():
            self.logger.debug('start %s (%s)', name, child.__class__.__name__)
            child.start()

    def stop(self):
        for name, child in self._compound_children.items():
            self.logger.debug('stop %s (%s)', name, child.__class__.__name__)
            child.stop()

    def join(self, end_comps=False):
        for name, child in self._compound_children.items():
            if end_comps and not child.is_pipe_end():
                continue
            self.logger.debug('join %s (%s)', name, child.__class__.__name__)
            child.join()
