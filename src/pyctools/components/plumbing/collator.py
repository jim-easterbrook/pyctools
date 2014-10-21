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

"""Collator.

Merges two inputs to produce a set of co-timed frames.

"""

__all__ = ['Collator']

from collections import deque

from guild.actor import *

from pyctools.core import Component

class Collator(Component):
    inputs = ['input1', 'input2']

    def __init__(self):
        super(Collator, self).__init__(with_outframe_pool=True)
        self.in_frames1 = deque()
        self.in_frames2 = deque()
        self.out_frames = deque()

    @actor_method
    def new_out_frame(self, frame):
        self.out_frames.append(frame)
        self.collate()

    @actor_method
    def input1(self, frame):
        self.in_frames1.append(frame)
        self.collate()

    @actor_method
    def input2(self, frame):
        self.in_frames2.append(frame)
        self.collate()

    def collate(self):
        while True:
            if not self.out_frames:
                return
            if not (self.in_frames1 and self.in_frames2):
                return
            # get frame from first input
            in_frame1 = self.in_frames1.popleft()
            if not in_frame1:
                self.output(None)
                self.stop()
                return
            # get frame from second input
            in_frame2 = self.in_frames2.popleft()
            if not in_frame2:
                self.output(None)
                self.stop()
                return
            # check frame numbers
            if in_frame1.frame_no < in_frame2.frame_no:
                # keep second input for another time
                self.in_frames2.appendleft(in_frame2)
                continue
            elif in_frame1.frame_no > in_frame2.frame_no:
                # keep first input for another time
                self.in_frames1.appendleft(in_frame1)
                continue
            out_frame = self.out_frames.popleft()
            out_frame.initialise(in_frame1)
            out_frame.data = in_frame1.data
            for comp in in_frame2.data:
                out_frame.data.append(comp)
            self.output(out_frame)
