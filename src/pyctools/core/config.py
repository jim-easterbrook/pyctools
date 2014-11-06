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

__docformat__ = 'restructuredtext en'

import collections
import copy

class ConfigLeafNode(object):
    """Base class for configuration nodes.

    :keyword object value: Initial value of the node.

    :keyword bool dynamic: Whether the value can be changed while the
        component is running. Not currently used anywhere.

    :keyword object min_value: Minimum value of the node, for types
        where it's relevant.

    :keyword object max_value: Maximum value of the node, for types
        where it's relevant.

    """
    def __init__(self, value=None, dynamic=False, min_value=None, max_value=None):
        self.value = value
        self.dynamic = dynamic
        self.min_value = min_value
        self.max_value = max_value
        self.default = value

    def get(self):
        return self.value

    def set(self, value):
        if not self.validate(value):
            raise ValueError(str(value))
        self.value = value

    def clip(self, value):
        if self.max_value is not None:
            value = min(value, self.max_value)
        if self.min_value is not None:
            value = max(value, self.min_value)
        return value

    def __repr__(self):
        return repr(self.value)

class ConfigPath(ConfigLeafNode):
    """File pathname configuration node.

    """
    def validate(self, value):
        return isinstance(value, str)

class ConfigInt(ConfigLeafNode):
    """Integer configuration node.

    """
    def __init__(self, **kw):
        super(ConfigInt, self).__init__(**kw)
        if self.value is None:
            self.value = self.clip(0)
            self.default = self.value

    def validate(self, value):
        return isinstance(value, int) and self.clip(value) == value

class ConfigFloat(ConfigLeafNode):
    """Float configuration node.

    """
    def __init__(self, decimals=8, wrapping=False, **kw):
        super(ConfigFloat, self).__init__(**kw)
        self.decimals = decimals
        self.wrapping = wrapping
        if self.value is None:
            self.value = self.clip(0.0)
            self.default = self.value

    def validate(self, value):
        return isinstance(value, float) and self.clip(value) == value

class ConfigStr(ConfigLeafNode):
    """String configuration node.

    """
    def validate(self, value):
        return isinstance(value, str)

class ConfigEnum(ConfigLeafNode):
    """'Enum' configuration node.

    The value can be one of a list of choices.

    """
    def __init__(self, choices, extendable=False, **kw):
        super(ConfigEnum, self).__init__(value=choices[0], **kw)
        self.choices = list(choices)
        self.extendable = extendable

    def validate(self, value):
        if self.extendable and value not in self.choices:
            self.choices.append(value)
        return value in self.choices

class ConfigParent(ConfigLeafNode):
    """Parent configuration node.

    Stores a set of child nodes in a :py:class:`dict`.

    """
    def __init__(self):
        super(ConfigParent, self).__init__(value={})

    def validate(self, value):
        return isinstance(value, dict)

    def __repr__(self):
        result = {}
        for key, value in self.value.items():
            if value.value != value.default:
                result[key] = value
        return repr(result)

    def __getitem__(self, key):
        return self.value[key].get()

    def __setitem__(self, key, value):
        if key in self.value:
            self.value[key].set(value)
        else:
            self.value[key] = value

class ConfigGrandParent(ConfigParent):
    """Grandparent configuration node.

    Stores a set of :py:class:`ConfigParent` nodes in a
    :py:class:`dict`.

    """
    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, value):
        self.value[key] = value

class ConfigMixin(object):
    """Add a config tree to a pyctools component.

    """
    def __init__(self):
        self.config = ConfigParent()
        self._configmixin_queue = collections.deque()

    def get_config(self):
        """Get a copy of the component's current configuration.

        Using a copy allows the config to be updated in a threadsafe
        manner while the component is running. Use
        :py:meth:`set_config` method to update the component's
        configuration after making changes to the copy.

        :return: Copy of component's configuration.

        :rtype: :py:class:`ConfigParent`

        """
        # get any queued changes
        self.update_config()
        # make copy to allow changes without affecting running
        # component
        return copy.deepcopy(self.config)

    def set_config(self, config):
        """Update the component's configuration.

        Use the :py:meth:`get_config` method to get a copy of the
        component's configuration, update that copy then call
        :py:meth:`set_config` to update the component. This enables
        the configuration to be changed in a threadsafe manner while
        the component is running, and allows several values to be
        changed at once.

        :param ConfigParent config: New configuration.

        """
        # put copy of config on queue for running component
        self._configmixin_queue.append(copy.deepcopy(config))

    def update_config(self):
        """Pull any changes made with :py:meth:`set_config`.

        Call this from within your component before using any config
        values to ensure you have the latest values set by the user.

        :return: Whether the config was updated.
        :rtype: bool

        """
        result = False
        while self._configmixin_queue:
            self.config = self._configmixin_queue.popleft()
            result = True
        return result
