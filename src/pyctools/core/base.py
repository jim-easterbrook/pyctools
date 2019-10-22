#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2014-19  Pyctools contributors
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

__all__ = ['Component', 'Transformer', 'InputBuffer', 'ObjectPool',
           'ThreadEventLoop']
__docformat__ = 'restructuredtext en'

from collections import deque
import logging
import threading
import time
import weakref

from .config import ConfigMixin, ConfigInt
from .frame import Frame, Metadata

logger = logging.getLogger(__name__)


class InputBuffer(object):
    """Input object buffer.

    :py:class:`~pyctools.core.frame.Frame` objects sent to the component
    are placed on a thread-safe queue before notifying the component
    that an input is available.

    :param callable notify: a thread-safe function to be called when an
        input frame is available.

    """
    def __init__(self, notify, **kwds):
        super(InputBuffer, self).__init__(**kwds)
        self.notify = notify
        self.queue = deque()

    def input(self, frame):
        """Put a frame object on the input queue (thread-safe).

        :param object frame: the input
            :py:class:`~pyctools.core.frame.Frame` object.

        """
        self.queue.append(frame)
        self.notify()

    def available(self):
        """Get length of input queue (thread-safe).

        :rtype: int

        """
        return len(self.queue)

    def peek(self, idx=0):
        """Get a frame object from the input queue without removing it
        from the queue (thread-safe).

        :keyword int idx: the queue position to fetch. Defaults the 0,
            the oldest frame in the queue.

        :rtype: object

        """
        return self.queue[idx]

    def get(self):
        """Get the oldest frame object from the input queue, removing it
        from the queue (thread-safe).

        :rtype: object

        """
        return self.queue.popleft()


class ThreadEventLoop(threading.Thread):
    """Event loop using :py:class:`threading.Thread`.

    This is the standard Pyctools event loop. It runs a component in a
    Python thread, allowing Pyctools components to run "concurrently".

    The event loop provides three methods that the owning component
    should "adopt" as its own: :py:meth:`start`, :py:meth:`running` &
    :py:meth:`join`.

    The owner component must provide four methods that the event loop
    calls in response to events: :py:meth:`~Component.start_event`,
    :py:meth:`~Component.stop_event`,
    :py:meth:`~Component.new_frame_event` &
    :py:meth:`~Component.new_config_event`.

    :param Component owner: the component that is using this event
        loop instance.

    .. automethod:: start()

    .. automethod:: join(timeout=None)

    """
    # rename method from threading.Thread
    running = threading.Thread.is_alive

    def __init__(self, owner, **kwds):
        super(ThreadEventLoop, self).__init__(**kwds)
        self.owner = owner
        self.daemon = True
        self.incoming = deque()

    def queue_command(self, command):
        """Put a command on the queue to be called in the component's
        thread.

        :param callable command: the method to be invoked, e.g.
            :py:meth:`~Component.new_frame_event`.

        """
        self.incoming.append(command)

    def run(self):
        """The actual event loop.

        Calls the ``owner``'s :py:meth:`~Component.start_event` method,
        then calls its :py:meth:`~Component.new_frame_event` and
        :py:meth:`~Component.new_config_event` methods as required until
        :py:meth:`~Component.stop` is called. Finally the ``owner``'s
        :py:meth:`~Component.stop_event` method is called before the
        thread terminates.

        """
        try:
            self.owner.start_event()
            while True:
                while not self.incoming:
                    time.sleep(0.01)
                while self.incoming:
                    command = self.incoming.popleft()
                    if command is None:
                        raise StopIteration()
                    command()
        except StopIteration:
            pass
        except Exception as ex:
            logger.exception(ex)
        self.owner.stop_event()


class Component(ConfigMixin):
    """Base class for all Pyctools components, *ie* objects to be used
    in processing pipelines / graph networks.

    By default every component has one input and one output. To help
    other software introspect the component the input and output names
    are listed in :py:attr:`~Component.inputs` and
    :py:attr:`~Component.outputs`. Redefine these attributes if your
    component has different inputs and outputs.

    The base class creates a thread-safe input buffer for each of your
    :py:attr:`~Component.inputs`. This allows the component to run in
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
    pairs or a ``config`` :py:class:`dict` to a component's constructor.
    These values are applied after calling :py:meth:`initialise`.

    :cvar bool ~Component.with_outframe_pool: Whether to use an outframe
        pool.

    :cvar list ~Component.inputs: The component's inputs.

    :cvar list ~Component.outputs: The component's outputs.

    :cvar class ~Component.event_loop: The type of event loop to
        use. Default is :py:class:`ThreadEventLoop`.

    :ivar logging.Logger logger: logging object for the component.

    :param dict config: Initial configuration values.

    """
    with_outframe_pool = True   #:
    inputs = ['input']          #:
    outputs = ['output']        #:
    event_loop = ThreadEventLoop

    def __init__(self, config={}, **kwds):
        super(Component, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)    #:
        # create event loop instance and adopt some of its methods
        self._event_loop = self.event_loop(owner=self)
        self.start = self._event_loop.start
        self.running = self._event_loop.running
        self.join = self._event_loop.join
        # set up inputs and outputs
        self.input_buffer = {}
        self.outframe_pool = {}
        # final initialisation
        self.initialise()
        if self.with_outframe_pool:
            self.config['outframe_pool_len'] = ConfigInt(3, min_value=2)
        for key, value in kwds.items():
            self.config[key] = value
        for key, value in config.items():
            self.config[key] = value
        # create a threadsafe buffer for each input and adopt its input method
        for name in self.inputs:
            self.input_buffer[name] = InputBuffer(self.new_frame)
            setattr(self, name, self.input_buffer[name].input)
        # initialise output connections lists
        self._component_connections = {}
        for name in self.outputs:
            self._component_connections[name] = []

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

        This method is called before :py:data:`None` is sent to all the
        component's outputs, so you can use it to flush any remaining
        output.

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

        Creates the output frame pools (if used) then calls
        :py:meth:`on_start`. Creating the output frame pools now allows
        their size to be configured before starting the component.

        """
        # create object pool for each output
        if self.with_outframe_pool:
            self.update_config()
            for name in self.outputs:
                self.outframe_pool[name] = ObjectPool(
                    Frame, self.new_frame, self.config['outframe_pool_len'])
        try:
            self.on_start()
        except Exception as ex:
            self.logger.exception(ex)
            raise StopIteration()

    def stop(self):
        """Thread-safe method to stop the component."""
        self._event_loop.queue_command(None)

    def stop_event(self):
        """Called by the event loop when it is stopped.

        Calls :py:meth:`on_stop`, then sends :py:data:`None` to each
        output to shut down the rest of the processing pipeline.

        """
        self.logger.debug('stopping')
        try:
            self.on_stop()
        except Exception as ex:
            self.logger.exception(ex)
        for name in self.outputs:
            self.send(name, None)

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
        for name in self.outputs:
            if self._component_connections[name]:
                return False
        return True

    def new_config(self):
        """Thread-safe method to alert the component to new config
        values.

        """
        self._event_loop.queue_command(self.new_config_event)

    def new_config_event(self):
        """Called by the event loop when new config is available.

        """
        try:
            self.on_set_config()
        except Exception as ex:
            self.logger.exception(ex)
            raise StopIteration()

    def new_frame(self):
        """Thread-safe method to alert the component to a new input or
        output frame.

        Called by the component's input buffer(s) when an input frame
        arrives, and by its output frame pool(s) when a new output frame
        is available.

        """
        self._event_loop.queue_command(self.new_frame_event)

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
        input buffer's :py:meth:`~InputBuffer.peek` method to get the
        frame without removing it from the buffer. See the
        :py:class:`~pyctools.components.colourspace.matrix.Matrix`
        component for an example.

        """
        # check output frames are available
        for out_pool in self.outframe_pool.values():
            if not out_pool.available():
                return
        # check input frames are available, and get current frame numbers
        frame_nos = {}
        for in_buff in self.input_buffer.values():
            if not in_buff.available():
                return
            in_frame = in_buff.peek()
            if in_frame is None:
                raise StopIteration()
            if in_frame.frame_no >= 0:
                frame_nos[in_buff] = in_frame.frame_no
            else:
                # discard any superseded 'static' input
                while in_buff.available() > 1 and in_buff.peek(1) is not None:
                    in_buff.get()
        if len(frame_nos) > 1:
            frame_no = max(frame_nos.values())
            # discard old frames that can never be used
            for in_buff in frame_nos:
                while frame_nos[in_buff] < frame_no and in_buff.available() > 1:
                    in_buff.get()
                    in_frame = in_buff.peek()
                    if in_frame is None:
                        raise StopIteration()
                    frame_nos[in_buff] = in_frame.frame_no
            # check for complete set of matching frame numbers
            if min(frame_nos.values()) != max(frame_nos.values()):
                return
        # now have a full set of correlated inputs to process
        try:
            self.process_frame()
        except StopIteration:
            raise
        except Exception as ex:
            self.logger.exception(ex)
            raise StopIteration()

    def process_frame(self):
        """Process an input frame (or set of frames).

        Derived classes must implement this method, unless they have no
        inputs and do not use any output frame pools.

        It is called when all input buffers and all output frame pools
        have a frame available. The derived class should use the
        buffers' and frame pools' :py:meth:`~ObjectPool.get` methods to
        get the input and output frames, do its processing, and then
        call the output :py:meth:`send` methods to send the results to
        the next components in the pipeline.

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
        input_name = self.inputs[0]
        output_name = self.outputs[0]
        in_frame = self.input_buffer[input_name].get()
        out_frame = self.outframe_pool[output_name].get()
        out_frame.initialise(in_frame)
        if self.transform(in_frame, out_frame):
            self.send(output_name, out_frame)
        else:
            raise StopIteration()

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
    has used up all of the objects in its pool it has to wait for the
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
        is available, e.g. :py:meth:`Component.new_frame`.

    :param int size: The maximum number of objects allowed to exist at
        any time.

    """
    def __init__(self, factory, notify, size, **kwds):
        super(ObjectPool, self).__init__(**kwds)
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
