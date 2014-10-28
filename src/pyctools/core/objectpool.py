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

__all__ = ['ObjectPool']

import weakref

class ObjectPool(object):
    def __init__(self, factory, size, callback):
        super(ObjectPool, self).__init__()
        self.factory = factory
        self.callback = callback
        self.obj_list = []
        # send first objects
        for i in range(size):
            self.new_object()

    def release(self, obj):
        self.obj_list.remove(obj)
        self.new_object()

    def new_object(self):
        obj = self.factory()
        self.obj_list.append(weakref.ref(obj, self.release))
        self.callback(obj)
