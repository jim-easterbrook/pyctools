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

"""Compound component.

Encapsulates several components into one. Closely modeled on
Kamaelia's 'Graphline' component
(http://www.kamaelia.org/Components/pydoc/Kamaelia.Chassis.Graphline.html).
Components are linked within the compound and to the outside world
according to the 'linkages' parameter.

The child components' config parent nodes are gathered into one
ConfigGrandParent. The child names (as used in the linkages) are
prepended to their config. E.g. if you have a component you've named
'src', its 'outframe_pool_len' config is now called
'src.outframe_pool_len'.

"""

from .config import ConfigGrandParent

class Compound(object):
    def __init__(self, **kw):
        super(Compound, self).__init__()
        # get child components
        self.children = {}
        for key in kw:
            if key == 'linkages':
                continue
            self.children[key] = kw[key]
        # set up linkages
        self.outputs = {}
        for source in kw['linkages']:
            src, outbox = source
            dest, inbox = kw['linkages'][source]
            if src == 'self':
                setattr(self, inbox, getattr(self.children[dest], inbox))
            elif dest == 'self':
                self.outputs[inbox] = (src, outbox)
            else:
                self.children[src].bind(outbox, self.children[dest], inbox)

    def bind(self, source, dest, destmeth):
        src, outbox = self.outputs[source]
        self.children[src].bind(outbox, dest, destmeth)

    def get_config(self):
        config = ConfigGrandParent(self.__class__.__name__)
        for name, child in self.children.iteritems():
            child_config = child.get_config()
            child_config.name = name
            config.append(child_config)
        return config

    def set_config(self, config):
        for child_config in config.children:
            self.children[child_config.name].set_config(child_config)

    def go(self):
        self.start()
        return self

    def start(self):
        for child in self.children.values():
            child.start()

    def stop(self):
        for child in self.children.values():
            child.stop()

    def join(self):
        for child in self.children.values():
            child.join()
