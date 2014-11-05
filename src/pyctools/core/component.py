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

"""Component base class."""

__all__ = ['Component']
__docformat__ = 'restructuredtext en'

import logging

from guild.actor import *

from .config import ConfigMixin, ConfigInt
from .frame import Frame
from .metadata import Metadata
from .objectpool import ObjectPool

class Component(Actor, ConfigMixin):
    """Base class for all Pyctools components, i.e. objects designed
    to be used in processing pipelines (or networks).

    By default every component has one input and one output. To help
    other software introspect the component their names are stored in
    :py:attr:`inputs` and :py:attr:`outputs`. Redefine these
    attributes if your component has different inputs and outputs.

    Each input must be a method of your component with the
    :py:meth:`guild.actor.actor_method` decorator. Similarly, each
    output must be a stub method with the
    :py:meth:`guild.actor.late_bind_safe` decorator. The base class
    includes methods for the default input and output.

    To help with load balancing components can have a limited size
    :py:class:`~.objectpool.ObjectPool` of output
    :py:class:`~.frame.Frame` objects. To use this your component must
    have a :py:meth:`new_out_frame` method with the
    :py:meth:`guild.actor.actor_method` decorator. This method is
    called when a new output frame is available. See the
    :py:class:`~.transformer.Transformer` class for an example.

    Every component also has configuration methods. See
    :py:class:`~.config.ConfigMixin` for more information.

    :keyword bool with_outframe_pool: Whether to use an outframe pool.

    """
    inputs = ['input']
    outputs = ['output']

    def __init__(self, with_outframe_pool=False):
        super(Component, self).__init__()
        ConfigMixin.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._component_with_outframe_pool = with_outframe_pool
        if self._component_with_outframe_pool:
            self.config['outframe_pool_len'] = ConfigInt(min_value=2, value=3)
        self.initialise()

    def initialise(self):
        """Over ride this in your derived class if you want to do any
        initialisation, such as adding to the config object.

        """
        pass

    def process_start(self):
        """Set up the outframe pool, if there is one.

        If you over ride this in your component, don't forget to call
        the base class method.

        """
        if self._component_with_outframe_pool:
            self.update_config()
            self._component_outframe_pool = ObjectPool(
                Frame, self.config['outframe_pool_len'], self.new_out_frame)

    @actor_method
    def new_out_frame(self, frame):
        """new_out_frame(frame)

        Receive a new output frame from the pool.

        If your component has an outframe pool this method is called
        when a previously used frame is deleted, allowing a new frame
        to be created.

        :param Frame frame: The newly available output frame.

        """
        raise NotImplemented()
