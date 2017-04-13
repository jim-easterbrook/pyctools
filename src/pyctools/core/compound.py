#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-17  Pyctools contributors
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

from .config import ConfigGrandParent

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

    Note the use of ``'self'`` in the ``linkages`` parameter to denote
    the compound object's own inputs and outputs. These are connected
    directly to the child components with no runtime overhead. There is
    no performance disadvantage from using compound objects.

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

    :keyword dict config: Additional config to be applied to the
        components before they are connected.

    """
    def __init__(self, config={}, linkages={}, **kw):
        super(Compound, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.inputs = []
        self.outputs = []
        # get child components
        self._compound_children = {}
        for key, value in kw.items():
            self._compound_children[key] = value
        # apply config
        for key, value in config.items():
            cnf = self._compound_children[key].get_config()
            for k, v in value.items():
                cnf[k] = v
            self._compound_children[key].set_config(cnf)
        # set up linkages
        self._compound_linkages = linkages
        self._compound_outputs = {}
        for source in linkages:
            src, outbox = source
            targets = linkages[source]
            if isinstance(targets[0], six.string_types):
                # not a list of pairs, so make it into one
                targets = zip(targets[0::2], targets[1::2])
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
        config = ConfigGrandParent()
        for name, child in self._compound_children.items():
            child_config = child.get_config()
            config[name] = child_config
        return config

    def set_config(self, config):
        """See :py:meth:`pyctools.core.config.ConfigMixin.set_config`."""
        for name, child_config in config.value.items():
            self._compound_children[name].set_config(child_config)

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
