#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-16  Pyctools contributors
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

__all__ = ['Component', 'Transformer', 'ObjectPool', 'ThreadEventLoop']
__docformat__ = 'restructuredtext en'

from collections import deque
import logging
import threading
import time
import weakref

from .config import ConfigMixin, ConfigInt
from .frame import Frame, Metadata

class InputBuffer(object):
    def __init__(self, notify, **kwds):
        super(InputBuffer, self).__init__(**kwds)
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
        return self.queue.popleft()


class ThreadEventLoop(threading.Thread):
    """Event loop using :py:class:`threading.Thread`.

    This is the standard Pyctools event loop. It runs a component in a
    Python thread, allowing Pyctools components to run "concurrently".

    The event loop provides four methods that the owning component
    should "adopt" as its own: :py:meth:`start`, :py:meth:`stop`,
    :py:meth:`running` & :py:meth:`join`.

    The owner component must provide four methods that the event loop
    calls in response to events: :py:meth:`~Component.start_event`,
    :py:meth:`~Component.stop_event`,
    :py:meth:`~Component.new_frame_event` &
    :py:meth:`~Component.new_config_event`. It must also provide a
    :py:attr:`~Component.logger` object.

    :param Component owner: the Pyctools component that is using this
        instance of :py:class:`ThreadEventLoop`.

    .. automethod:: start()

    .. automethod:: join(timeout=None)

    """

    # rename method from threading.Thread
    running = threading.Thread.is_alive

    def __init__(self, owner, **kwds):
        super(ThreadEventLoop, self).__init__(**kwds)
        self.daemon = True
        self.owner = owner
        self.incoming = deque()

    def run(self):
        """The actual event loop.

        Calls the ``owner``'s :py:meth:`~Component.start_event` method,
        then calls its :py:meth:`~Component.new_frame_event` and
        :py:meth:`~Component.new_config_event` methods as required until
        :py:meth:`stop` is called. Finally the ``owner``'s
        :py:meth:`~Component.stop_event` method is called before the
        thread terminates.

        """
        self.owner.start_event()
        while True:
            while not self.incoming:
                time.sleep(0.01)
            command = self.incoming.popleft()
            if command is None:
                break
            try:
                command()
            except Exception as ex:
                self.owner.logger.exception(ex)
                break
        self.owner.stop_event()

    def stop(self):
        """Thread-safe method to stop the component."""
        self.incoming.append(None)

    def new_frame(self):
        """Thread-safe method to alert the component to a new input or
        output frame.

        Called by the component's input buffer(s) when an input frame
        arrives, and by its output frame pool(s) when a new output frame
        is available.

        """
        self.incoming.append(self.owner.new_frame_event)

    def new_config(self):
        """Thread-safe method to alert the component to new config
        values.

        """
        self.incoming.append(self.owner.new_config_event)


class Component(ConfigMixin):
    """Base class for all Pyctools components, *ie* objects to be used
    in processing pipelines / graph networks.

    By default every component has one input and one output. To help
    other software introspect the component the input and output names
    are listed in :py:attr:`~Component.inputs` and
    :py:attr:`~Component.outputs`. Redefine these attributes if your
    component has different inputs and outputs.

    The base class creates a thread-safe input buffer for each of your
    :py:attr:`~Component.inputs`. This allows each component to run in
    its own thread.

    To help with load balancing, components usually have a limited size
    :py:class:`ObjectPool` of output :py:class:`~.frame.Frame` objects.
    To disable this your class should set
    :py:attr:`~Component.with_outframe_pool` to ``False``. The base
    class creates an output frame pool for each of your
    :py:attr:`~Component.outputs`.

    A :py:class:`logging.Logger` object is created for every component.
    Use this to report any errors or warnings from your component,
    rather than using :py:func:`print` statements. The component may get
    used in situations where there is no console to print messages to.

    Every component also has configuration methods. See
    :py:class:`~.config.ConfigMixin` for more information. The
    configuration can be initialised by passing appropriate (key, value)
    pairs to a component's constructor. These values are applied after
    calling :py:meth:`initialise`.

    :cvar bool ~Component.with_outframe_pool: Whether to use an outframe
        pool.

    :cvar list ~Component.inputs: The component's inputs.

    :cvar list ~Component.outputs: The component's outputs.

    :cvar object ~Component.event_loop: The type of event loop to use.
        Default is :py:class:`ThreadEventLoop`.

    :ivar logging.Logger logger: logging object for the component.

    :param dict config: Initial configuration values.

    """
    with_outframe_pool = True
    inputs = ['input']
    outputs = ['output']
    event_loop = ThreadEventLoop

    def __init__(self, config={}, **kwds):
        super(Component, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)    #:
        # create event loop and adopt some of its methods
        component_event_loop = self.event_loop(self)
        self.start = component_event_loop.start
        self.stop = component_event_loop.stop
        self.running = component_event_loop.running
        self.join = component_event_loop.join
        self.new_frame = component_event_loop.new_frame
        self.new_config = component_event_loop.new_config
        # set up inputs and outputs
        self.input_buffer = {}
        self.outframe_pool = {}
        if self.with_outframe_pool:
            self.config['outframe_pool_len'] = ConfigInt(min_value=2, value=3)
        # final initialisation
        self.initialise()
        for key, value in kwds.items():
            self.config[key] = value
        for key, value in config.items():
            self.config[key] = value
        # create a threadsafe buffer for each input and adopt its input method
        for input in self.inputs:
            self.input_buffer[input] = InputBuffer(self.new_frame)
            setattr(self, input, self.input_buffer[input].input)
        # create object pool for each output
        if self.with_outframe_pool:
            for output in self.outputs:
                self.outframe_pool[output] = ObjectPool(Frame, self.new_frame)
        # initialise output connections lists
        self._component_connections = {}
        for output in self.outputs:
            self._component_connections[output] = []

    def initialise(self):
        """Over ride this in your derived class if you need to do any
        initialisation, such as adding to the config object.

        """
        pass

    def on_connect(self, output_name):
        """Over ride this in your derived class if you need to do
        anything when an output is connected.

        """
        pass

    def on_set_config(self):
        """Over ride this in your derived class if you need to do
        anything when the configuration is updated.

        The config isn't actually changed until
        :py:meth:`~.config.ConfigMixin.update_config` is called, so be
        sure to do this in your method.

        """
        pass

    def on_start(self):
        """Over ride this in your derived class if you need to do
        anything when the component is started.

        """
        pass

    def on_stop(self):
        """Over ride this in your derived class if you need to do
        anything when the component is stopped.

        This method is called before :py:data:`None` is sent to all
        outputs, so you can use it to flush any remaining output.

        """
        pass

    def send(self, output_name, frame):
        """Send an output frame.

        The frame is sent to each input the output is connected to. If
        there are no connections this is a null operation with little
        overhead.

        :param str output_name: the output to use. Must be a member of
            :py:attr:`~Component.outputs`.

        :param Frame frame: the frame to send.

        """
        for input_method in self._component_connections[output_name]:
            input_method(frame)

    def connect(self, output_name, input_method):
        """Connect an output to any callable object.

        :py:meth:`on_connect` is called after the connection is made to
        allow components to do something when an output is conected.

        :param str output_name: the output to connect. Must be a member
            of :py:attr:`~Component.outputs`.

        :param callable input_method: the thread-safe callable to invoke
            when :py:meth:`send` is called.

        """
        self.logger.debug('connect "%s"', output_name)
        if self.running():
            raise RuntimeError('Cannot connect running component')
        self._component_connections[output_name].append(input_method)
        self.on_connect(output_name)

    def bind(self, source, dest, destmeth):
        """Guild compatible version of :py:meth:`connect`.

        This allows Pyctools components to be used in `Guild
        <https://github.com/sparkslabs/guild>`_ pipelines.

        """
        self.connect(source, getattr(dest, destmeth))

    def start_event(self):
        """Called by the event loop when it is started.

        Calls :py:meth:`on_start`, then starts any output frame pools.

        """
        self.on_start()
        if self.with_outframe_pool:
            self.update_config()
            for output in self.outframe_pool.values():
                output.start(self.config['outframe_pool_len'])

    def stop_event(self):
        """Called by the event loop when it is stopped.

        Calls :py:meth:`on_stop`, then sends :py:data:`None` to each
        output to shut down the rest of the processing pipeline.

        """
        self.logger.debug('stopping')
        self.on_stop()
        for output in self.outputs:
            self.send(output, None)

    def is_pipe_end(self):
        """Is component the last one in a pipeline.

        When waiting for a network of components to finish processing
        it's not necessary to wait for every component to stop, and in
        many cases they won't all stop anyway.

        This method makes it easier to choose which components to wait
        for. See the :py:mod:`Compound <.compound>` component for an
        example.

        :rtype: :py:class:`bool`

        """
        for output in self.outputs:
            if self._component_connections[output]:
                return False
        return True

    def new_config_event(self):
        """Called by the event loop when new config is available.

        """
        self.on_set_config()

    def new_frame_event(self):
        """Called by the event loop when a new input or output frame is
        available.

        Inputs are correlated by comparing their frame numbers. If there
        is a complete set of inputs, and all output frame pools are
        ready, the :py:meth:`process_frame` method is called.

        If an input frame has a negative frame number it is not
        correlated with other inputs, it is merely required to exist.
        This allows frame objects to be used as control inputs when
        processing video sequences. The derived class should use the
        input buffer's ``peek`` method to get the frame without removing
        it from the buffer. See the
        :py:class:`~pyctools.components.colourspace.matrix.Matrix`
        component for an example.

        """
        # check output frames are available
        for output in self.outframe_pool.values():
            if not output.available():
                return
        # check input frames are available, and get current frame number
        frame_no = 0
        for input in self.input_buffer.values():
            if not input.available():
                return
            in_frame = input.peek()
            if in_frame is None:
                input.get()
                self.stop()
                return
            frame_no = max(frame_no, in_frame.frame_no)
        # check for complete set of matching frame numbers
        for input in self.input_buffer.values():
            in_frame = input.peek()
            # discard old frames that can never be used
            while input.available() > 1 and in_frame.frame_no < frame_no:
                input.get()
                in_frame = input.peek()
            # check for matching frame number
            if in_frame.frame_no >= 0 and in_frame.frame_no != frame_no:
                return
        # now have a full set of correlated inputs to process
        self.process_frame()
        # might be more on the queue, so run again (via event loop)
        self.new_frame()

    def process_frame(self):
        """Process an input frame (or set of frames).

        Derived classes must implement this method, unless they have no
        inputs and do not use any output frame pools.

        It is called when all input buffers and all output frame pools
        have a frame available. The derived class should use the
        buffers' and frame pools' ``get`` methods to get the input and
        output frames, do its processing, and then call the output
        methods to send the results to the next components in the
        pipeline.

        See the :py:class:`Transformer` base class for a typical
        implementation.

        """
        raise NotImplemented()


class Transformer(Component):
    """Base class for simple components with one input and one output.

    When an input :py:class:`~.frame.Frame` object is received, and an
    output :py:class:`~.frame.Frame` object is available from a pool,
    the :py:meth:`~Transformer.transform` method is called to do the
    component's actual work.

    """
    def process_frame(self):
        """Get the input and output frame, then call
        :py:meth:`transform`.

        """
        in_frame = self.input_buffer['input'].get()
        out_frame = self.outframe_pool['output'].get()
        out_frame.initialise(in_frame)
        if self.transform(in_frame, out_frame):
            self.send('output', out_frame)
        else:
            self.stop()

    def transform(self, in_frame, out_frame):
        """Process an input :py:class:`~.frame.Frame`.

        You must implement this in your derived class.

        Typically you will set ``out_frame``'s data to a new image
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
    """Output object "pool".

    In a pipeline of components it is useful to have some way of "load
    balancing", to prevent the first component in the pipeline doing all
    its work before the next component starts. A simple way to do this
    is to use a limited size "pool" of objects. When the first component
    has used up all of the objects in the pool it has to wait for the
    next component in the pipeline to consume and release an object thus
    ensuring the first component doesn't get too far ahead.

    This object pool uses Python's :py:class:`weakref.ref` class to
    trigger the release of a new object when Python no longer holds a
    reference to an old object, i.e. when it gets deleted.

    Note that the ``factory`` and ``notify`` functions must both be
    thread safe. They are usually called from the thread that deleted
    the old object, not the :py:class:`ObjectPool` owner's thread.

    :param callable factory: The function to call to create new
        objects.

    :param callable notify: A function to call when a new object
        is available, e.g. :py:meth:`ThreadEventLoop.new_frame`.

    """
    def __init__(self, factory, notify, **kwds):
        super(ObjectPool, self).__init__(**kwds)
        self.factory = factory
        self.notify = notify
        self.ref_list = []
        self.obj_list = deque()

    def start(self, size):
        """Start the object pool.

        Call this when the component is ready to run. Setting the pool
        size here allows it to be part of the component's config,
        adjusted after initialisation but before the component is run.

        :param int size: The maximum number of objects allowed to exist
            at any time.

        """
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
        """Number of objects currently available from the pool.

        :rtype: :py:class:`int`

        """
        return len(self.obj_list)

    def get(self):
        """Get an object from the pool.

        :rtype: the object or :py:data:`None`

        """
        if self.obj_list:
            return self.obj_list.popleft()
        return None
