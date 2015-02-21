#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-15  Pyctools contributors
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

"""Distribute frames to several components.

This component allows one component's output to be connected to
several components' inputs. It initially has two outputs (``output0``
and ``output1``) but new outputs are created as needed to ensure there
is always at least one free.

Any data sent to ``input`` is sent to every connected output. The data
is not required to be a Pyctools
:py:class:`~pyctools.core.frame.Frame`.

"""

import logging

from guild.actor import actor_method
from guild.components import Splitter

from pyctools.core.config import ConfigMixin

__all__ = ['Busbar']
__docformat__ = 'restructuredtext en'

class Busbar(Splitter, ConfigMixin):
    inputs = ['input']

    def __init__(self):
        super(Busbar, self).__init__()
        ConfigMixin.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.outputs = ['output0', 'output1']
        self._busbar_connections = {}

    def input(self, data):
        """input(self, data)

        """
        # base class method uses queued invocation
        super(Busbar, self).input(data)
        if data is None:
            # use queued stop, should happen after outputs are sent
            self.queued_stop()

    @actor_method
    def queued_stop(self):
        self.stop()

    def is_pipe_end(self):
        if self._busbar_connections:
            return False
        return True

    def onStop(self):
        self.logger.debug('stopping')
        super(Busbar, self).onStop()

    def connect(self, output_name, input_method):
        self.logger.debug('connect "%s"', output_name)
        self._busbar_connections[output_name] = input_method
        self.subscribe(self._busbar_connections[output_name])
        if output_name not in self.outputs:
            self.outputs.append(output_name)
        n = 0
        while len(self.outputs) <= len(self._busbar_connections):
            name = 'output%d' % n
            if name not in self.outputs:
                self.outputs.append(name)
            n += 1
        self.outputs.sort()

    def bind(self, source, dest, destmeth):
        self.connect(source, getattr(dest, destmeth))
