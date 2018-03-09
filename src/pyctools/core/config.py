#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-18  Pyctools contributors
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

"""Component configuration classes.

The :py:class:`ConfigMixin` mixin class can be used with any component
to provide a hierarchical tree of named configuration values. Each
configuration value node has a fixed type and can be configured to
have constraints such as maximum and minimum values.

Configuration values are accessed in a dictionary-like manner. During
a component's initialisation you should create the required
configuration nodes like this::

    self.config['zlen'] = ConfigInt(value=100, min_value=1)
    self.config['looping'] = ConfigEnum(choices=('off', 'repeat'))

Subsequently the config object behaves more like a dictionary::

    self.config['zlen'] = 250
    ...
    zlen = self.config['zlen']

Users of a component can initialise its configuration by passing
key-value pairs to the component's constructor::

    resize = Resize(xup=xup, xdown=xdown)

The configuration can be changed, even when the component is running,
with the :py:meth:`~ConfigMixin.get_config` and
:py:meth:`~ConfigMixin.set_config` methods::

    cfg = resize.get_config()
    cfg['xup'] = 3
    cfg['xdown'] = 4
    resize.set_config(cfg)

Or, more simply::

    resize.set_config({'xup': 3, 'xdown': 4})

Note that these methods are thread-safe and make a copy of the
configuration tree. This ensures that all your configuration changes
are applied together, some time after calling
:py:meth:`~ConfigMixin.set_config`.

.. autosummary::
   :nosignatures:

   ConfigMixin
   ConfigParent
   ConfigGrandParent
   ConfigInt
   ConfigFloat
   ConfigBool
   ConfigStr
   ConfigPath
   ConfigEnum
   ConfigLeafNode

"""

__docformat__ = 'restructuredtext en'

import collections
import copy
import os.path
import six

class ConfigLeafNode(object):
    """Mixin class for configuration nodes.

    :keyword object value: Initial value of the node.

    :keyword object min_value: Minimum value of the node, for types
        where it's relevant.

    :keyword object max_value: Maximum value of the node, for types
        where it's relevant.

    """
    def parser_add(self, parser, key):
        parser.add_argument('--' + key, default=self, **self.parser_kw)

    def get(self):
        """Return the config item's current value."""
        return self

    def update(self, value):
        """Adjust the config item's value."""
        kwds = dict(self.__dict__)
        if 'parser_kw' in kwds:
            del(kwds['parser_kw'])
        return self.__class__(value, **kwds)


class ConfigInt(ConfigLeafNode, int):
    """Integer configuration node.

    """
    parser_kw = {'type' : int, 'metavar' : 'n'}

    def __new__(cls, value=0, min_value=None, max_value=None):
        if min_value is not None and value < min_value:
            value = min_value
        if max_value is not None and value > max_value:
            value = max_value
        self = super(ConfigInt, cls).__new__(cls, value)
        self.min_value = min_value
        self.max_value = max_value
        return self

    def __getnewargs__(self):
        return int(self), self.min_value, self.max_value


class ConfigBool(ConfigInt):
    """Boolean configuration node.

    """
    parser_kw = {'type' : bool, 'metavar' : 'b'}

    def __new__(cls, value=False, *args, **kwds):
        if value == 'on':
            value = True
        elif value == 'off':
            value = False
        else:
            value = bool(value)
        return super(ConfigBool, cls).__new__(cls, value, *args, **kwds)


class ConfigFloat(ConfigLeafNode, float):
    """Float configuration node.

    :keyword int decimals: How many decimal places to use when
        displaying the value.

    :keyword bool wrapping: Should the value change to min_value when
        incremented beyond max_value or *vice versa*.

    """
    parser_kw = {'type' : float, 'metavar' : 'x'}

    def __new__(cls, value=0.0, min_value=None, max_value=None,
                decimals=8, wrapping=False):
        if min_value is not None and value < min_value:
            value = min_value
        if max_value is not None and value > max_value:
            value = max_value
        self = super(ConfigFloat, cls).__new__(cls, value)
        self.min_value = min_value
        self.max_value = max_value
        self.decimals = decimals
        self.wrapping = wrapping
        return self

    def __getnewargs__(self):
        return (float(self), self.min_value, self.max_value,
                self.decimals, self.wrapping)


class ConfigStr(ConfigLeafNode, six.text_type):
    """String configuration node.

    """
    parser_kw = {'metavar' : 'str'}

    def __new__(cls, value=''):
        return super(ConfigStr, cls).__new__(cls, value)
        return self


class ConfigPath(ConfigStr):
    """File pathname configuration node.

    """
    parser_kw = {'metavar' : 'path'}

    def __new__(cls, value='', exists=True):
        if value:
            value = os.path.abspath(value)
            if exists:
                if not os.path.isfile(value):
                    value = ''
            else:
                if not os.path.isdir(os.path.dirname(value)):
                    value = ''
        else:
            value = ''
        self = super(ConfigPath, cls).__new__(cls, value)
        self.exists = exists
        return self

    def __getnewargs__(self):
        return six.text_type(self), self.exists


class ConfigEnum(ConfigStr):
    """'Enum' configuration node.

    The value can be one of a list of choices.

    :keyword list choices: a list of strings that are the possible
        values of the config item. Initial value is the first in the
        list.

    :keyword bool extendable: can the choices list be extended by
        setting new values.

    """
    def __new__(cls, value=None, choices=[], extendable=False):
        choices = list(choices)
        if not value:
            value = choices[0]
        elif value not in choices:
            if extendable:
                choices.append(value)
            else:
                raise ValueError(str(value))
        self = super(ConfigEnum, cls).__new__(cls, value)
        self.choices = choices
        self.extendable = extendable
        self.parser_kw = {'metavar' : 'str'}
        if not self.extendable:
            self.parser_kw['choices'] = self.choices
        return self

    def __getnewargs__(self):
        return six.text_type(self), self.choices, self.extendable


class ConfigParent(ConfigLeafNode, collections.OrderedDict):
    """Parent configuration node.

    Stores a set of child nodes in a :py:class:`dict`.

    """
    def __repr__(self):
        result = {}
        for key, value in self.items():
            result[key] = value
        return repr(result)

    def parser_add(self, parser, prefix=''):
        if prefix:
            prefix += '.'
        for key, value in self.items():
            value.parser_add(parser, prefix + key)

    def parser_set(self, args):
        for key, value in vars(args).items():
            parts = key.split('.')
            while len(parts) > 1:
                value = {parts[-1] : value}
                del parts[-1]
            key = parts[0]
            self[key] = value

    def __setitem__(self, key, value):
        if not isinstance(value, ConfigLeafNode):
            value = self[key].update(value)
        super(ConfigParent, self).__setitem__(key, value)

    def update(self, other=[], **kw):
        if isinstance(other, dict):
            other = other.items()
        if other:
            for key, value in other:
                self[key] = value
        for key, value in kw.items():
            self[key] = value
        return self


class ConfigGrandParent(ConfigParent):
    """Grandparent configuration node.

    Stores a set of :py:class:`ConfigParent` nodes in a
    :py:class:`dict`.

    """
    pass


class ConfigMixin(object):
    """Add a config tree to a pyctools component.

    """
    def __init__(self, **kwds):
        super(ConfigMixin, self).__init__(**kwds)
        self.config = ConfigParent()
        self._configmixin_queue = collections.deque()

    def get_config(self):
        """Get a copy of the component's current configuration.

        Using a copy allows the config to be updated in a threadsafe
        manner while the component is running. Use the
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
        # notify component, using thread safe method
        self.new_config()

    def update_config(self):
        """Pull any changes made with :py:meth:`set_config`.

        Call this from within your component before using any config
        values to ensure you have the latest values set by the user.

        :return: Whether the config was updated.
        :rtype: bool

        """
        result = False
        while self._configmixin_queue:
            config = self._configmixin_queue.popleft()
            self.config.update(config)
            result = True
        return result
