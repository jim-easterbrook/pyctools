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

"""Component base classes.

.. autosummary::

   Component
   Transformer
   ObjectPool

"""

__all__ = ['Component', 'Transformer', 'ObjectPool']
__docformat__ = 'restructuredtext en'

from collections import deque
import logging
import weakref

from guild.actor import *

from .config import ConfigMixin, ConfigInt
from .frame import Frame, Metadata

class InputBuffer(object):
    def __init__(self, notify):
        self.notify = notify
        self.queue = deque()

    def input(self, frame):
        self.queue.append(frame)
        self.notify()

    def available(self):
        return len(self.queue)

    def peek(self):
        return self.queue[0]

    def get(self):
        if not self.queue:
            return None
        return self.queue.popleft()


class Component(Actor, ConfigMixin):
    """Base class for all Pyctools components, i.e. objects designed
    to be used in processing pipelines (or graph networks).

    By default every component has one input and one output. To help
    other software introspect the component their names are listed in
    :py:attr:`inputs` and :py:attr:`outputs`. Redefine these
    attributes if your component has different inputs and outputs.

    Each input must be a method of your component with the
    :py:meth:`guild.actor.actor_method` decorator. Similarly, each
    output must be a stub method with the
    :py:meth:`guild.actor.late_bind_safe` decorator. The base class
    includes methods for the default input and output.

    To help with load balancing components can have a limited size
    :py:class:`ObjectPool` of output :py:class:`~.frame.Frame`
    objects. To use this your class must set ``with_outframe_pool`` to
    ``True`` and have a :py:meth:`new_out_frame` method with the
    :py:meth:`guild.actor.actor_method` decorator. This method is
    called when a new output frame is available. See the
    :py:class:`Transformer` class for an example.

    A :py:class:`logging.Logger` object is created for every
    component. Use this to report any errors or warnings from your
    component, rather than using ``print`` statements. The component
    may get used in situations where there is no console to print
    messages to.

    Every component also has configuration methods. See
    :py:class:`~.config.ConfigMixin` for more information. The
    configuration can be initialised by passing appropriate key, value
    pairs to a component's constructor. These values are applied after
    calling :py:meth:`initialise`.

    :cvar bool with_outframe_pool: Whether to use an outframe pool.

    :cvar list inputs: The component's inputs.

    :cvar list outputs: The component's outputs.

    :ivar logger: :py:class:`logging.Logger` object for the component.

    :param dict config: Initial configuration values.

    """
    with_outframe_pool = False
    inputs = ['input']
    outputs = ['output']

    def __init__(self, **config):
        super(Component, self).__init__()
        ConfigMixin.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.input_buffer = {}
        self.outframe_pool = {}
        if self.with_outframe_pool:
            self.config['outframe_pool_len'] = ConfigInt(min_value=2, value=3)
        self.initialise()
        for key, value in config.items():
            self.config[key] = value
        # create a threadsafe buffer for each input and adopt its input method
        for input in self.inputs:
            self.input_buffer[input] = InputBuffer(self.notify)
            setattr(self, input, self.input_buffer[input].input)
        # initialise outputs to default "do nothing" output
        for output in self.outputs:
            if output != 'output':
                setattr(self, output, self.output)

    def initialise(self):
        """Over ride this in your derived class if you need to do any
        initialisation, such as adding to the config object.

        """
        pass

    def process_start(self):
        """Set up the outframe pool, if there is one.

        If you over ride this in your component, don't forget to call
        the base class method.

        """
        if self.with_outframe_pool:
            self.update_config()
            for output in self.outputs:
                self.outframe_pool[output] = ObjectPool(
                    Frame, self.config['outframe_pool_len'], self.notify)

    @actor_method
    def notify(self):
        while True:
            # check output frames are available
            for output in self.outframe_pool.values():
                if not output.available():
                    return
            # check input frames are available
            for input in self.input_buffer.values():
                if not input.available():
                    return
            # test for 'None' input, and get current frame number
            frame_no = -1
            for input in self.input_buffer.values():
                in_frame = input.peek()
                if not in_frame:
                    for output in self.outputs:
                        getattr(self, output)(None)
                    self.stop()
                    return
                frame_no = max(frame_no, in_frame.frame_no)
            # discard old frames that can never be used
            OK = True
            for input in self.input_buffer.values():
                in_frame = input.peek()
                if in_frame.frame_no < 0:
                    # special case "static" inputs, only one required
                    while input.available() > 1:
                        input.get()
                elif in_frame.frame_no < frame_no:
                    input.get()
                    OK = False
            if not OK:
                continue
            # now have a full set of correlated inputs to process
            self.process_frame()


class Transformer(Component):
    """ A Transformer is a Pyctools component that has one input and
    one output. When an input :py:class:`~.frame.Frame` object is
    received, and an output :py:class:`~.frame.Frame` object is
    available from a pool, the ":py:meth:`~Transformer.transform`"
    method is called to do the component's actual work.

    """
    with_outframe_pool = True

    def process_frame(self):
        in_frame = self.input_buffer['input'].get()
        out_frame = self.outframe_pool['output'].get()
        out_frame.initialise(in_frame)
        if self.transform(in_frame, out_frame):
            self.output(out_frame)
        else:
            self.output(None)
            self.stop()
            return

    def transform(self, in_frame, out_frame):
        """Process an input :py:class:`~.frame.Frame`.

        You must implement this in your derived class.

        Typically you will set ``out_frame``'s data with new images
        created from ``in_frame``'s data. You must not modify the
        input :py:class:`~.frame.Frame` -- it might be being used by
        another component running in parallel!

        Return ``True`` if your processing was successful. Otherwise
        return ``False``, after logging an appropriate error message.

        :param Frame in_frame: The input frame to read.

        :param Frame out_frame: The output frame to write.

        :return: Should processing continue.

        :rtype: :py:class:`bool`

        """
        raise NotImplemented('transform')


class ObjectPool(object):
    """Object "pool".

    In a pipeline of processes it is useful to have some way of "load
    balancing", to prevent the first process in the pipeline doing all
    its work before the next process starts. A simple way to do this
    is to use a limited size "pool" of objects. When the first process
    has used up all of the objects in the pool it has to wait for the
    next process in the pipeline to consume and release an object thus
    ensuring it doesn't get too far ahead.

    This object pool uses Python's :py:class:`weakref.ref` class to
    trigger the release of a new object when Python no longer holds a
    reference to an old object, i.e. when it gets deleted.

    See the :py:class:`Transformer` source code for an example of how
    to add an outframe pool to a Pyctools :py:class:`Component`.

    :param callable factory: The function to call to create new
        objects.

    :param int size: The maximum number of objects allowed to exist at
        any time.

    :param callable notify: A function to call when a new object
        is available.

    """
    def __init__(self, factory, size, notify):
        super(ObjectPool, self).__init__()
        self.factory = factory
        self.notify = notify
        self.ref_list = []
        self.obj_list = deque()
        # create first objects
        for i in range(size):
            self._new_object()

    def _release(self, obj):
        self.ref_list.remove(obj)
        self._new_object()

    def _new_object(self):
        obj = self.factory()
        self.obj_list.append(obj)
        self.ref_list.append(weakref.ref(obj, self._release))
        self.notify()

    def available(self):
        return len(self.obj_list)

    def get(self):
        if self.obj_list:
            return self.obj_list.popleft()
        return None
