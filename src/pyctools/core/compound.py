#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-24  Pyctools contributors
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

__all__ = ['ComponentRunner', 'Compound', 'RunnableNetwork']
__docformat__ = 'restructuredtext en'

import logging

from .config import ConfigParent


class RunnableNetwork(object):
    """Encapsulate several components into one.

    This is the basic runnable network part of a :py:class:`Compound`
    component.

    :keyword Component name: Add ``Component`` to the network as
        ``name``. Can be repeated with different values of ``name``.

    :keyword dict linkages: A mapping from component outputs to
        component inputs.

    """
    inputs = []     #:
    outputs = []    #:
    children = {}   #:
    links = []      #:

    def __init__(self, linkages={}, **kw):
        super(RunnableNetwork, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.inputs = []
        self.outputs = []
        # get child components
        self.children = kw
        # set up linkages
        self._compound_outputs = {}
        self.links = []
        for source, targets in linkages.items():
            if isinstance(targets[0], str):
                # not a list of pairs, so make it into one
                targets = list(zip(targets[0::2], targets[1::2]))
            src, outbox = source
            for dest, inbox in targets:
                if src == 'self':
                    if hasattr(self, outbox):
                        self.logger.critical(
                            'cannot link (%s, %s) to more than one target',
                            src, outbox)
                    setattr(self, outbox, getattr(self.children[dest], inbox))
                    self.inputs.append(outbox)
                elif dest == 'self':
                    self._compound_outputs[inbox] = (src, outbox)
                    self.outputs.append(inbox)
                else:
                    self.children[src].connect_to(
                        outbox, getattr(self.children[dest], inbox))
                self.links.append(((src, outbox), (dest, inbox)))

    def go(self):
        """Guild compatible version of :py:meth:`start`."""
        self.start()
        return self

    def start(self):
        """Start the component running."""
        for name, child in self.children.items():
            self.logger.debug('start %s (%s)', name, child.__class__.__name__)
            child.start()

    def stop(self):
        """Thread-safe method to stop the component."""
        for name, child in self.children.items():
            self.logger.debug('stop %s (%s)', name, child.__class__.__name__)
            child.stop()

    def join(self, end_comps=False):
        """Wait for the compound component's children to stop running.

        :param bool end_comps: only wait for the components that end a
            pipeline. This is useful for complex graphs where it is
            normal for some components not to terminate.

        """
        for name, child in self.children.items():
            if end_comps and not child.is_pipe_end():
                continue
            self.logger.debug('join %s (%s)', name, child.__class__.__name__)
            child.join()

    def is_pipe_end(self):
        for src, outbox in self._compound_outputs.values():
            if not self.children[src].is_pipe_end():
                return False
        return True


class Compound(RunnableNetwork):
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
            cfg.update(config)
            cfg.update(kwds)
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
    no performance disadvantage from using compound objects. The
    ``'self'`` inboxes and outboxes are added to the component's
    :py:attr:`~Compound.inputs` and :py:attr:`~Compound.outputs` lists.

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

    The compound component's child components are stored in the
    :py:attr:`~Compound.children` dict. This must not be modified but
    may be useful if you need to know about the component's internals.

    The component's internal links are stored in the
    :py:attr:`~Compound.links` list. This also must not be modified but
    can be used for introspection. Each element is a ``(src_name,
    outbox), (dest_name, inbox)`` tuple.

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
        super(Compound, self).__init__(linkages=linkages, **kw)
        # set config
        self.config = ConfigParent(config_map=config_map)
        for name, child in self.children.items():
            self.config[name] = child.get_config()
        self.config.set_default(config=config)

    def connect_to(self, output_name, input_method):
        """Connect an output to any callable object.

        :param str output_name: the output to connect. Must be one of
            the ``'self'`` outputs in the ``linkages`` parameter.

        :param callable input_method: the thread-safe callable to invoke
            when :py:meth:`send` is called.

        """
        src, outbox = self._compound_outputs[output_name]
        self.children[src].connect_to(outbox, input_method)

    def bind(self, source, dest, destmeth):
        """Guild compatible version of :py:meth:`connect_to`.

        This allows Pyctools compound components to be used in `Guild
        <https://github.com/sparkslabs/guild>`_ pipelines.

        """
        self.connect_to(source, getattr(dest, destmeth))

    def get_config(self):
        """See :py:meth:`pyctools.core.config.ConfigMixin.get_config`."""
        return self.config.copy()

    def set_config(self, config):
        """See :py:meth:`pyctools.core.config.ConfigMixin.set_config`."""
        self.config.update(config)
        for name, child in self.children.items():
            child.set_config(self.config[name])


class ComponentRunner(object):
    """Run a compound component as a script.

    A :py:class:`Compound` component passed to :py:meth:`run_network`
    has its configuration turned into command line arguments. After
    parsing the command line the component is run until its pipeline end
    components have terminated.

    This is primarily used in scripts created by the
    :py:mod:`pyctools-editor <pyctools.tools.editor>` tool.

    """

    def run_network(self, comp):
        import argparse
        comp.set_config(comp.user_config)
        cnf = comp.get_config()
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        cnf.parser_add(parser)
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help='increase verbosity of log messages')
        args = parser.parse_args()
        logging.basicConfig(level=logging.ERROR - (args.verbose * 10))
        del args.verbose
        cnf.parser_set(args)
        comp.set_config(cnf)
        comp.start()
        self.do_loop(comp)
        comp.stop()
        comp.join()

    def do_loop(self, comp):
        try:
            comp.join(end_comps=True)
        except KeyboardInterrupt:
            pass
