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

"""Transformer base class.

A Transformer is a Pyctools component that has one input and one
output. When an input Frame object is received, and an output Frame
object is available from a pool, the "transform" method is called to
do the component's actual work.

"""

__all__ = ['Transformer']

from collections import deque

from guild.actor import *

from .component import Component

class Transformer(Component):
    def __init__(self):
        self._transformer_in_frames = deque()
        self._transformer_out_frames = deque()
        self._transformer_ready = True
        super(Transformer, self).__init__(with_outframe_pool=True)

    def set_ready(self, value):
        self._transformer_ready = value
        self._transformer_transform()

    @actor_method
    def input(self, frame):
        self._transformer_in_frames.append(frame)
        self._transformer_transform()

    @actor_method
    def new_out_frame(self, frame):
        self._transformer_out_frames.append(frame)
        self._transformer_transform()

    def _transformer_transform(self):
        while (self._transformer_ready and self._transformer_out_frames and
               self._transformer_in_frames):
            in_frame = self._transformer_in_frames.popleft()
            if not in_frame:
                self.output(None)
                self.stop()
                return
            out_frame = self._transformer_out_frames.popleft()
            out_frame.initialise(in_frame)
            if self.transform(in_frame, out_frame):
                self.output(out_frame)
            else:
                self.output(None)
                self.stop()
