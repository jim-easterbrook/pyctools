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

"""Component base class.

Base class for all Pyctools components, i.e. objects designed to be
used in processing pipelines (or networks).

Provides configuration via a tree of different node types for
different value types.

"""

__all__ = ['Component', 'ConfigPath', 'ConfigInt']

import copy
import logging

from guild.actor import *

from .frame import Frame
from .metadata import Metadata
from .objectpool import ObjectPool

class ConfigLeafNode(object):
    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

class ConfigPath(ConfigLeafNode):
    pass

class ConfigInt(ConfigLeafNode):
    pass

class ConfigGroupNode(object):
    def __init__(self, name):
        self.name = name
        self.children = []
        self.append = self.children.append

    def __getitem__(self, key):
        return self._child(key).get()

    def __setitem__(self, key, value):
        self._child(key).set(value)

    def _child(self, name):
        parts = name.split('.', 1)
        for child in self.children:
            if child.name == parts[0]:
                if len(parts) > 1:
                    return child._child(parts[1])
                return child
        raise KeyError()

class Component(Actor):
    def __init__(self, with_outframe_pool=False):
        super(Component, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.with_outframe_pool = with_outframe_pool
        self.config = ConfigGroupNode(self.__class__.__name__)
        if self.with_outframe_pool:
            self.config.append(ConfigInt('outframe_pool_len', 3))

    def get_config(self):
        # make copy to allow changes without affecting running
        # component
        return copy.deepcopy(self.config)

    def set_config(self, config):
        # single object assignment should be thread-safe, so can
        # update running component
        self.config = copy.deepcopy(config)

    def process_start(self):
        if self.with_outframe_pool:
            self.pool = ObjectPool(Frame, self.config['outframe_pool_len'])
            self.pool.bind("output", self, "new_frame")
            start(self.pool)

    def onStop(self):
        if self.with_outframe_pool:
            stop(self.pool)
