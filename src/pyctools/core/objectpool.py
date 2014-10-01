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

"""Object "pool".

In a pipeline of processes it is useful to have some way of "load
balancing", to prevent the first process in the pipeline doing all its
work before the next process starts. A simple way to do this is to use
a limited size "pool" of objects. When the first process has used all
of the objects in the pool it has to wait for the next process in the
pipeline to release an object (after consuming it) thus ensuring it
doesn't get too far ahead.

This object pool uses Python's "weakref" module to trigger the release
of a new object when Python no longer holds a reference to an old
object, i.e. when it gets deleted.

"""

from __future__ import print_function

import sys
import time
import weakref

from guild.actor import *

class ObjectPool(Actor):
    def __init__(self, factory, size):
        super(ObjectPool, self).__init__()
        self.factory = factory
        self.size = size
        self.obj_list = []

    def gen_process(self):
        for i in range(self.size):
            self.new_object()
            yield 1

    def release(self, obj):
        self.obj_list.remove(obj)
        self.new_object()

    def new_object(self):
        obj = self.factory()
        self.obj_list.append(weakref.ref(obj, self.release))
        self.output(obj)

def main():
    class Frame(object):
        pass

    class Source(Actor):
        def process_start(self):
            self.n = 0
            self.pool = ObjectPool(Frame, 3)
            self.pool.bind("output", self, "new_frame")
            start(self.pool)

        @actor_method
        def new_frame(self, frame):
            print('source', self.n)
            frame.n = self.n
            self.output(frame)
            self.n += 1

        def onStop(self):
            stop(self.pool)

    class Sink(Actor):
        @actor_method
        def input(self, frame):
            print('sink', frame.n)
            time.sleep(1.0)

    print('ObjectPool demonstration')
    source = Source()
    sink = Sink()
    pipeline(source, sink)
    start(source, sink)
    time.sleep(10)
    stop(source, sink)
    wait_for(source, sink)
    return 0

if __name__ == '__main__':
    sys.exit(main())
