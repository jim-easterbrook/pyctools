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

from guild.actor import *
from guild.components import Splitter

from pyctools.core.config import ConfigMixin

__all__ = ['Busbar']

class Busbar(Splitter, ConfigMixin):
    inputs = ['input']

    def __init__(self):
        super(Busbar, self).__init__()
        ConfigMixin.__init__(self)
        self.outputs = ['output0', 'output1']
        self._busbar_connections = {}

    @actor_method
    def publish(self, data):
        super(Busbar, self).publish(data)
        if data is None:
            self.stop()

    def bind(self, source, dest, destmeth):
        self._busbar_connections[source] = getattr(dest, destmeth)
        self.subscribe(self._busbar_connections[source])
        if source not in self.outputs:
            self.outputs.append(source)
        n = 0
        while len(self.outputs) <= len(self._busbar_connections):
            name = 'output%d' % n
            if name not in self.outputs:
                self.outputs.append(name)
            n += 1
        self.outputs.sort()
