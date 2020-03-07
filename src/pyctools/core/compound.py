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

__all__ = ['Compound']
__docformat__ = 'restructuredtext en'

import logging
import six

from .config import ConfigParent


class Compound(object):
    """Encapsulate several components into one.

    Closely modeled on `Kamaelia's 'Graphline' component
    <http://www.kamaelia.org/Components/pydoc/Kamaelia.Chassis.Graphline.html>`_.
    Components are linked within the compound and to the outside world
    according to the ``linkages`` parameter.

    For example, you could create an image resizer by connecting a
    :py:class:`~pyctools.components.interp.filtergenerator.FilterGenerator`
    to a :py:class:`~pyctools.components.interp.resize.Resize` as
    follows::

        def ImageResizer(config={}, **kwds):
            cfg = {'aperture': 16}
            cfg.update(kwds)
            cfg.update(config)
            return Compound(
                filgen = FilterGenerator(),
                resize = Resize(),
                config = cfg,
                config_map = {
                    'up'      : ('filgen.xup',   'resize.xup',
                                 'filgen.yup',   'resize.yup'),
                    'down'    : ('filgen.xdown', 'resize.xdown',
                                 'filgen.ydown', 'resize.ydown'),
                    'aperture': ('filgen.xaperture', 'filgen.yaperture'),
                    },
                linkages = {
                    ('self',   'input')  : ('resize', 'input'),
                    ('filgen', 'output') : ('resize', 'filter'),
                    ('resize', 'output') : ('self',    'output'),
                    }
                )

    Note the use of ``'self'`` in the ``linkages`` parameter to denote
    the compound object's own inputs and outputs. These are connected
    directly to the child components with no runtime overhead. There is
    no performance disadvantage from using compound objects.

    All the child components' configuration objects are gathered into
    one :py:class:`~.config.ConfigParent`. The child names are used to
    index the :py:class:`~.config.ConfigParent`'s dict. This allows
    access to any config item in any child::

        cfg = image_resizer.get_config()
        cfg.filgen.xup = 3
        cfg.filgen.xdown = 8
        cfg.filgen.yup = 3
        cfg.filgen.ydown = 8
        cfg.resize.xup = 3
        cfg.resize.xdown = 8
        cfg.resize.yup = 3
        cfg.resize.ydown = 8
        image_resizer.set_config(cfg)

    Compound components to be nested to any depth whilst still making
    their configuration available at the top level.

    The ``config_map`` allows multiple child components to be controlled
    by one configuration item. For each item there is a list of child
    config items, in parent.child form. For example, to change the
    scaling factor of the image resizer shown above (even while it's
    running!) you might do this::

        cfg = image_resizer.get_config()
        cfg.up = 3
        cfg.down = 8
        image_resizer.set_config(cfg)

    You can also adjust the configuration when the compound component is
    created by passing a :py:class:`dict` containing additional values.
    This allows the component's user to over-ride the default values.

    :keyword Component name: Add ``Component`` to the network as
        ``name``. Can be repeated with different values of ``name``.

    :keyword dict linkages: A mapping from component outputs to
        component inputs.

    :keyword dict config: Additional configuration to be applied to the
        components before they are connected.

    :keyword dict config_map: Mapping of top level configuration names
        to child component configuration names.

    """
    def __init__(self, config={}, config_map={}, linkages={}, **kw):
        super(Compound, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.inputs = []
        self.outputs = []
        # get child components
        self._compound_children = {}
        for key, value in kw.items():
            self._compound_children[key] = value
        # set config
        self.config = ConfigParent(config_map=config_map)
        for name, child in self._compound_children.items():
            self.config[name] = child.get_config()
        if config:
            self.set_config(config)
        # set up linkages
        self._compound_linkages = {}
        self._compound_outputs = {}
        for source in linkages:
            src, outbox = source
            targets = linkages[source]
            if isinstance(targets[0], six.string_types):
                # not a list of pairs, so make it into one
                targets = list(zip(targets[0::2], targets[1::2]))
            self._compound_linkages[source] = targets
            for dest, inbox in targets:
                if src == 'self':
                    if hasattr(self, outbox):
                        self.logger.critical(
                            'cannot link (%s, %s) to more than one target',
                            src, outbox)
                    setattr(self, outbox,
                            getattr(self._compound_children[dest], inbox))
                    self.inputs.append(outbox)
                elif dest == 'self':
                    self._compound_outputs[inbox] = (src, outbox)
                    self.outputs.append(inbox)
                else:
                    self._compound_children[src].connect(
                        outbox, getattr(self._compound_children[dest], inbox))

    def connect(self, output_name, input_method):
        """Connect an output to any callable object.

        :param str output_name: the output to connect. Must be one of
            the ``'self'`` outputs in the ``linkages`` parameter.

        :param callable input_method: the thread-safe callable to invoke
            when :py:meth:`send` is called.

        """
        src, outbox = self._compound_outputs[output_name]
        self._compound_children[src].connect(outbox, input_method)

    def bind(self, source, dest, destmeth):
        """Guild compatible version of :py:meth:`connect`.

        This allows Pyctools compound components to be used in `Guild
        <https://github.com/sparkslabs/guild>`_ pipelines.

        """
        self.connect(source, getattr(dest, destmeth))

    def get_config(self):
        """See :py:meth:`pyctools.core.config.ConfigMixin.get_config`."""
        return self.config.copy()

    def set_config(self, config):
        """See :py:meth:`pyctools.core.config.ConfigMixin.set_config`."""
        self.config = self.config.update(config)
        for name, child in self._compound_children.items():
            child.set_config(self.config[name])

    def go(self):
        """Guild compatible version of :py:meth:`start`."""
        self.start()
        return self

    def start(self):
        """Start the component running."""
        for name, child in self._compound_children.items():
            self.logger.debug('start %s (%s)', name, child.__class__.__name__)
            child.start()

    def stop(self):
        """Thread-safe method to stop the component."""
        for name, child in self._compound_children.items():
            self.logger.debug('stop %s (%s)', name, child.__class__.__name__)
            child.stop()

    def join(self, end_comps=False):
        """Wait for the compound component's children to stop running.

        :param bool end_comps: only wait for the components that end a
            pipeline. This is useful for complex graphs where it is
            normal for some components not to terminate.

        """
        for name, child in self._compound_children.items():
            if end_comps and not child.is_pipe_end():
                continue
            self.logger.debug('join %s (%s)', name, child.__class__.__name__)
            child.join()

    def is_pipe_end(self):
        for src, outbox in self._compound_outputs.values():
            if not self._compound_children[src].is_pipe_end():
                return False
        return True

    def input_connections(self, name):
        """Yield ordered list of connections to one child.

        Each result is a ((component, output), (component, input)) tuple.

        :param string name: the component whose input connections are
            wanted.

        """
        for input_name in self._compound_children[name].inputs:
            dest = name, input_name
            for src, dests in self._compound_linkages.items():
                if dest in dests:
                    yield src, dest

    def output_connections(self, name):
        """Yield ordered list of connections to one child.

        Each result is a ((component, output), (component, input)) tuple.

        :param string name: the component whose output connections are
            wanted.

        """
        for output_name in self._compound_children[name].outputs:
            src = name, output_name
            if src in self._compound_linkages:
                dests = self._compound_linkages[src]
                for dest in dests:
                    yield src, dest

    def all_connections(self):
        """Yield ordered list of all connections within the component.

        Each result is a ((component, output), (component, input)) tuple.

        """
        for src, dests in self._compound_linkages.items():
            for dest in dests:
                yield src, dest

    def components(self):
        """Yield list of all the component's children.

        Each result is a (name, component) tuple.

        """
        yield from self._compound_children.items()
