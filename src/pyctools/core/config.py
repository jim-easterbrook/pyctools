#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-19  Pyctools contributors
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
            '--' + key, default=self, help=' ', **self.parser_kw())

    def update(self, value):
        """Adjust the config item's value."""
        return self.__class__(value, **self.__dict__)


class ConfigInt(ConfigLeafNode, int):
    """Integer configuration node.

    :keyword object value: Initial value of the node.

    :keyword int default: Default value of the node.

    :keyword int min_value: Minimum permissible value.

    :keyword int max_value: Maximum permissible value.

    """
    def __new__(cls, value=0, default=None, min_value=None, max_value=None):
        if min_value is not None and value < min_value:
            value = min_value
        if max_value is not None and value > max_value:
            value = max_value
        return super(ConfigInt, cls).__new__(
            cls, value, default, min_value=min_value, max_value=max_value)

    def parser_kw(self):
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

    def parser_kw(self):
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

    def parser_kw(self):
        return {'type' : float, 'metavar' : 'x'}


class ConfigStr(ConfigLeafNode, six.text_type):
    """String configuration node.

    :keyword object value: Initial value of the node.

    :keyword str default: Default value of the node.

    """
    def __new__(cls, value='', default=None, **kwds):
        return super(ConfigStr, cls).__new__(cls, value, default, **kwds)

    def parser_kw(self):
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
                    raise ValueError(value)
            else:
                if not os.path.isdir(os.path.dirname(value)):
                    raise ValueError(value)
        return super(ConfigPath, cls).__new__(cls, value, default, exists=exists)

    def __getnewargs__(self):
        return six.text_type(self), self.default, self.exists

    def parser_kw(self):
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

    def parser_kw(self):
        result = {'metavar' : 'str'}
        if not self.extendable:
            result['choices'] = self.choices
        return result


class ConfigParent(ConfigLeafNode, collections.OrderedDict):
    """Parent configuration node.

    Stores a set of child nodes in a :py:class:`dict`.

    """
    def __new__(cls):
        return super(ConfigParent, cls).__new__(cls, value={}, default=None)

    def __repr__(self):
        result = []
        for key, value in self.items():
            if value != value.default:
                result.append("'{}': {!r}".format(key, value))
        return '{' + ', '.join(result) + '}'

    def audit_string(self):
        result = ''
        details = []
        for key, value in self.items():
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
            self._parser_update(key, value)

    def _parser_update(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        if key in self:
            value = self[key].update(value)
        elif not isinstance(value, ConfigLeafNode):
            logger.error('unknown config item: %s, %s', key, value)
            return
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
    def _parser_update(self, key, value):
        child, sep, grandchild = key.partition('.')
        self[child]._parser_update(grandchild, value)


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
