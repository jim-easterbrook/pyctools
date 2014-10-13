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

"""Configuration classes.

Provides configuration via a tree of different node types for
different value types.

"""

import copy

class ConfigLeafNode(object):
    def __init__(self, name, value=None, dynamic=False):
        self.name = name
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        if not self.validate(value):
            raise ValueError(str(value))
        self.value = value

class ConfigPath(ConfigLeafNode):
    def validate(self, value):
        return True

class ConfigInt(ConfigLeafNode):
    def validate(self, value):
        return True

class ConfigEnum(ConfigLeafNode):
    def __init__(self, name, choices, **kw):
        super(ConfigEnum, self).__init__(name, value=choices[0], **kw)
        self.choices = choices

    def validate(self, value):
        return value in self.choices

class ConfigParent(object):
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
        raise KeyError(name)

class ConfigGrandParent(ConfigParent):
    pass

class ConfigMixin(object):
    def __init__(self):
        self.config = ConfigParent(self.__class__.__name__)

    def get_config(self):
        # make copy to allow changes without affecting running
        # component
        return copy.deepcopy(self.config)

    def set_config(self, config):
        # single object assignment should be thread-safe, so can
        # update running component
        self.config = copy.deepcopy(config)
