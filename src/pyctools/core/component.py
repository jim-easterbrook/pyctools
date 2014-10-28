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

"""

__all__ = ['Component']

import logging

from guild.actor import *

from .config import ConfigMixin, ConfigInt
from .frame import Frame
from .metadata import Metadata
from .objectpool import ObjectPool

class Component(Actor, ConfigMixin):
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
        if self._component_with_outframe_pool:
            self.update_config()
            self._component_outframe_pool = ObjectPool(
                Frame, self.config['outframe_pool_len'], self.new_out_frame)
