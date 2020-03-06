#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-20  Pyctools contributors
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

The :py:class:`ConfigMixin` mixin class is used with every component to
provide a hierarchical tree of named configuration values. Each
configuration value node has a fixed type and can be configured to have
constraints such as maximum and minimum values.

Configuration values are accessed in a dictionary-like manner. During
a component's initialisation you should create the required
configuration nodes like this::

    self.config['zlen'] = ConfigInt(value=100, min_value=1)
    self.config['looping'] = ConfigEnum(choices=('off', 'repeat'))

Subsequently the config object behaves more like a dictionary::

    self.config['zlen'] = 250
    ...
    zlen = self.config['zlen']

Users of a component can initialise its configuration by passing a
``config`` :py:class:`dict` or key-value pairs to the component's
constructor::

    resize = Resize(config={'xup': xup}, xdown=xdown)

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
import logging
import os.path
import six

logger = logging.getLogger(__name__)


class ConfigLeafNode(object):
    """Mixin class for configuration nodes.

    """
    def __new__(cls, value, default, **kwds):
        self = super(ConfigLeafNode, cls).__new__(cls, value)
        if default is None:
            default = value
        self.default = default
        for key, value in kwds.items():
            setattr(self, key, value)
        return self

    def parser_add(self, parser, key):
        parser.add_argument(
            '--' + key, default=self, help=' ', **self._parser_kw())

    def update(self, value):
        """Adjust the config item's value."""
        return self.__class__(value, **self.__dict__)

    def copy(self):
        return self.update(self)


class ConfigInt(ConfigLeafNode, int):
    """Integer configuration node.

    :keyword object value: Initial value of the node.

    :keyword int default: Default value of the node.

    :keyword int min_value: Minimum permissible value.

    :keyword int max_value: Maximum permissible value.

    :keyword bool wrapping: Should the value change to min_value when
        incremented beyond max_value or *vice versa*.

    """
    def __new__(cls, value=0, default=None, min_value=None, max_value=None,
                wrapping=False):
        if min_value is not None and value < min_value:
            value = min_value
        if max_value is not None and value > max_value:
            value = max_value
        return super(ConfigInt, cls).__new__(
            cls, value, default, min_value=min_value, max_value=max_value,
            wrapping=wrapping)

    @staticmethod
    def _parser_kw():
        return {'type' : int, 'metavar' : 'n'}


class ConfigBool(ConfigInt):
    """Boolean configuration node.

    :keyword object value: Initial value of the node.

    :keyword bool default: Default value of the node.

    """
    def __new__(cls, value=False, default=None, **kwds):
        if value == 'on':
            value = True
        elif value == 'off':
            value = False
        else:
            value = bool(value)
        return super(ConfigBool, cls).__new__(cls, value, default)

    def __repr__(self):
        return str(bool(self))

    @staticmethod
    def _parser_kw():
        return {'type' : bool, 'metavar' : 'b'}


class ConfigFloat(ConfigLeafNode, float):
    """Float configuration node.

    :keyword object value: Initial value of the node.

    :keyword float default: Default value of the node.

    :keyword float min_value: Minimum permissible value.

    :keyword float max_value: Maximum permissible value.

    :keyword int decimals: How many decimal places to use when
        displaying the value.

    :keyword bool wrapping: Should the value change to min_value when
        incremented beyond max_value or *vice versa*.

    """
    def __new__(cls, value=0.0, default=None, min_value=None, max_value=None,
                decimals=8, wrapping=False):
        if min_value is not None and value < min_value:
            value = min_value
        if max_value is not None and value > max_value:
            value = max_value
        return super(ConfigFloat, cls).__new__(
            cls, value, default, min_value=min_value, max_value=max_value,
            decimals=decimals, wrapping=wrapping)

    @staticmethod
    def _parser_kw():
        return {'type' : float, 'metavar' : 'x'}


class ConfigStr(ConfigLeafNode, six.text_type):
    """String configuration node.

    :keyword object value: Initial value of the node.

    :keyword str default: Default value of the node.

    """
    def __new__(cls, value='', default=None, **kwds):
        return super(ConfigStr, cls).__new__(cls, value, default, **kwds)

    @staticmethod
    def _parser_kw():
        return {'metavar' : 'str'}


class ConfigPath(ConfigStr):
    """File pathname configuration node.

    :keyword object value: Initial value of the node.

    :keyword str default: Default value of the node.

    :keyword bool exists: If ``True``, value must be an existing file.

    """
    def __new__(cls, value='', default=None, exists=True):
        if value:
            value = os.path.abspath(value)
            if exists:
                if not os.path.isfile(value):
                    logger.warning('file "%s" does not exist', value)
            else:
                directory = os.path.dirname(value)
                if not os.path.isdir(directory):
                    logger.warning('directory "%s" does not exist', directory)
        return super(ConfigPath, cls).__new__(cls, value, default, exists=exists)

    def __getnewargs__(self):
        return six.text_type(self), self.default, self.exists

    @staticmethod
    def _parser_kw():
        return {'metavar' : 'path'}


class ConfigEnum(ConfigStr):
    """'Enum' configuration node.

    The value can be one of a list of choices.

    :keyword str value: Initial value of the node.

    :keyword str default: Default value of the node.

    :keyword list choices: a list of strings that are the possible
        values of the config item. If value is unset the first in the
        list is used.

    :keyword bool extendable: can the choices list be extended by
        setting new values.

    """
    def __new__(cls, value=None, default=None, choices=[], extendable=False):
        choices = list(choices)
        if not value:
            value = choices[0]
        elif value not in choices:
            if extendable:
                choices.append(value)
            else:
                raise ValueError(str(value))
        return super(ConfigEnum, cls).__new__(
            cls, value, default, choices=choices, extendable=extendable)

    def __getnewargs__(self):
        return six.text_type(self), self.default, self.choices, self.extendable

    def _parser_kw(self):
        result = {'metavar' : 'str'}
        if not self.extendable:
            result['choices'] = self.choices
        return result


class ConfigParent(object):
    """Parent configuration node.

    Stores a set of child nodes in a :py:class:`dict`. In a
    :py:class:`~.compound.Compound` component the children are
    themselves :py:class:`ConfigParent` nodes, allowing components to be
    nested to any depth whilst making their configuration accessible
    from the top level.

    The ``config_map`` is used in :py:class:`~.compound.Compound`
    components to allow multiple child components to be controlled by
    one config value.

    """
    default = {}

    def __init__(self, config_map={}):
        super(ConfigParent, self).__init__()
        self._config_map = config_map
        self._value = {}

    def __repr__(self):
        result = []
        for key, value in self._value.items():
            if value != value.default:
                result.append("'{}': {!r}".format(key, value))
        return '{' + ', '.join(result) + '}'

    def __getattr__(self, name):
        if name[0] != '_':
            return self[name]
        return super(ConfigParent, self).__getattr__(name)

    def __setattr__(self, name, value):
        if name[0] != '_':
            self[name] = value
            return
        super(ConfigParent, self).__setattr__(name, value)

    def __len__(self):
        if self._config_map:
            return len(self._config_map)
        return len(self._value)

    def __getitem__(self, key):
        if key in self._config_map:
            return self[self._config_map[key][0]]
        child, sep, grandchild = key.partition('.')
        if grandchild:
            return self[child][grandchild]
        return self._value[key]

    def __setitem__(self, key, value):
        if key in self._config_map:
            for item in self._config_map[key]:
                self[item] = value
            return
        child, sep, grandchild = key.partition('.')
        if grandchild:
            self[child][grandchild] = value
            return
        if key in self._value:
            value = self._value[key].update(value)
        elif not isinstance(value, (ConfigLeafNode, ConfigParent)):
            logger.error('unknown config item: %s, %s', key, value)
            return
        self._value[key] = value

    def __iter__(self):
        if self._config_map:
            yield from self._config_map
        else:
            yield from self._value

    def items(self):
        for key in self:
            yield key, self[key]

    def values(self):
        for key in self:
            yield self[key]

    def audit_string(self):
        result = ''
        details = []
        for key, value in self._value.items():
            if value == value.default:
                continue
            details.append('{}: {!r}'.format(key, value))
            line = ', '.join(details)
            if len(line) < 76:
                continue
            if len(details) > 1:
                line = ', '.join(details[:-1])
                details = details[-1:]
            else:
                details = []
            result += '    ' + line + '\n'
        if details:
            line = ', '.join(details)
            result += '    ' + line + '\n'
        return result

    def parser_add(self, parser, prefix=''):
        """Add config to an :py:class:`argparse.ArgumentParser` object.

        The parser’s :py:meth:`~argparse.ArgumentParser.add_argument`
        method is called for each config item. The argument name is
        constructed from the parent and item names, with a dot
        separator.

        :param argparse.ArgumentParser parser: The argument parser object.

        :keyword str prefix: The parent node name.

        """
        if prefix:
            prefix += '.'
        for key, value in self.items():
            value.parser_add(parser, prefix + key)

    def parser_set(self, args):
        """Set config from an :py:class:`argparse.Namespace` object.

        Call this method with the return value from
        :py:meth:`~argparse.ArgumentParser.parse_args`.

        :param argparse.Namespace args: The populated
            :py:class:`argparse.Namespace` object.

        """
        for key, value in vars(args).items():
            self[key] = value

    def update(self, value):
        for key, value in value.items():
            self[key] = value
        return self

    def copy(self):
        copy = self.__class__(config_map=self._config_map)
        for key, value in self._value.items():
            copy._value[key] = value.copy()
        return copy


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
        # make copy to allow changes without affecting running component
        return self.config.copy()

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
        # get copy of current config
        cfg = self.get_config()
        # update it with new values
        cfg = cfg.update(config)
        # put modified copy on queue for running component
        self._configmixin_queue.append(cfg)
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
            self.config = self._configmixin_queue.popleft()
            result = True
        return result
