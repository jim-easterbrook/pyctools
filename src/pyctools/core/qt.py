#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2015-24  Pyctools contributors
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

__all__ = ['ComponentRunner', 'QtEventLoop', 'QtThreadEventLoop']
__docformat__ = 'restructuredtext en'

from collections import deque, namedtuple
from functools import wraps
import logging
import os
import sys
import time

from pyctools.core.compound import ComponentRunner as ComponentRunnerBase

logger = logging.getLogger(__name__)

if 'PYCTOOLS_QT' in os.environ:
    qt_package = os.environ['PYCTOOLS_QT']
else:
    qt_package = 'PyQt5'

if qt_package == 'PyQt5':
    from PyQt5 import QtCore, QtWidgets
    from PyQt5.QtCore import pyqtSlot as QtSlot
elif qt_package == 'PyQt6':
    from PyQt6 import QtCore, QtWidgets
    from PyQt6.QtCore import pyqtSlot as QtSlot
elif qt_package == 'PySide2':
    from PySide2 import QtCore, QtWidgets
    from PySide2.QtCore import Slot as QtSlot
elif qt_package == 'PySide6':
    from PySide6 import QtCore, QtWidgets
    from PySide6.QtCore import Slot as QtSlot
else:
    raise ImportError(f'Unrecognised qt_package value "{qt_package}"')


if qt_package in ('PySide2', 'PySide6'):
    qt_version_info = QtCore.__version_info__
else:
    qt_version_info = namedtuple(
        'qt_version_info', ('major', 'minor', 'micro'))._make(
            map(int, QtCore.QT_VERSION_STR.split('.')))


if qt_package == 'PyQt6':
    LowEventPriority = QtCore.Qt.EventPriority.LowEventPriority.value
else:
    LowEventPriority = int(QtCore.Qt.EventPriority.LowEventPriority)


# exec gets renamed to exec_ in PySide2
def execute(widget, *arg, **kwds):
    if qt_package == 'PySide2':
        return widget.exec_(*arg, **kwds)
    return widget.exec(*arg, **kwds)


# decorator for methods called by Qt that logs any exception raised
def catch_all(func):
    @wraps(func)
    def wrapper(*args, **kwds):
        try:
            return func(*args, **kwds)
        except Exception as ex:
            logger.exception(ex)
    return wrapper


# create unique event type
_queue_event = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

class QtEventLoop(QtCore.QObject):
    """Event loop using the Qt "main thread" (or "GUI thread").

    Use this event loop if your component is a Qt widget or needs to run
    in the main Qt thread for any other reason. See the
    :py:mod:`~pyctools.components.qt.qtdisplay.QtDisplay` component for
    an example.

    Pyctools event loops are described in more detail in the
    :py:class:`~.base.ThreadEventLoop` documentation.

    """
    def __init__(self, owner, **kwds):
        super(QtEventLoop, self).__init__(**kwds)
        self._owner = owner
        self._running = False
        self._incoming = deque()
        # put start_event command on queue for later
        self._incoming.append(self._owner.start_event)

    def event(self, event):
        if event.type() != _queue_event:
            return super(QtEventLoop, self).event(event)
        event.accept()
        try:
            while self._incoming:
                command = self._incoming.popleft()
                if command is None:
                    raise StopIteration()
                command()
            return True
        except StopIteration:
            pass
        except Exception as ex:
            logger.exception(ex)
        if self._running:
            self._owner.stop_event()
            self._running = False
            self._quit()
        return True

    def queue_command(self, command):
        """Put a command on the queue to be called in the component's
        thread.

        :param callable command: the method to be invoked, e.g.
            :py:meth:`~Component.new_frame_event`.

        """
        # put command on queue for later
        self._incoming.append(command)
        if self._running:
            # send event to process queue
            QtCore.QCoreApplication.postEvent(
                self, QtCore.QEvent(_queue_event), LowEventPriority)

    def _quit(self):
        pass

    def start(self):
        """Start the component's event loop (thread-safe).

        After the event loop is started the Qt thread calls the
        component's :py:meth:`~Component.start_event` method, then calls
        its :py:meth:`~Component.new_frame_event` and
        :py:meth:`~Component.new_config_event` methods as required until
        :py:meth:`~Component.stop` is called. Finally the component's
        :py:meth:`~Component.stop_event` method is called before the
        event loop terminates.

        """
        if self._running:
            raise RuntimeError('Component {} is already running'.format(
                self._owner.__class__.__name__))
        self._running = True
        # start_event is already in queue, send signal to process it
        QtCore.QCoreApplication.postEvent(
            self, QtCore.QEvent(_queue_event), LowEventPriority)

    def join(self, timeout=3600):
        """Wait until the event loop terminates or ``timeout`` is
        reached.

        This method is not meaningful unless called from the Qt "main
        thread", which is almost certainly the thread in which the
        component was created.

        :keyword float timeout: timeout in seconds.

        """
        start = time.time()
        while self._running:
            now = time.time()
            maxtime = timeout + start - now
            if maxtime <= 0:
                return
            QCoreApplication.processEvents(
                QEventLoop.AllEvents, int(maxtime * 1000))

    def running(self):
        """Is the event loop running.

        :rtype: :py:class:`bool`

        """
        return self._running


class QtThreadEventLoop(QtEventLoop):
    """Event loop using a Qt "worker thread".

    Use this event loop if your component is a Qt component that does
    not need to run in the main thread. This allows a Pyctools component
    to send or receive Qt signals, giving easy integration with other Qt
    components.

    I have experimented with using :py:class:`QtThreadEventLoop` instead
    of :py:class:`~.base.ThreadEventLoop` in all the components in a
    network. Surprisingly it ran at the same speed.

    Pyctools event loops are described in more detail in the
    :py:class:`~.base.ThreadEventLoop` documentation.

    .. automethod:: queue_command()

    .. automethod:: start()

    .. automethod:: running()

    """
    def __init__(self, owner, **kwds):
        super(QtThreadEventLoop, self).__init__(owner, **kwds)
        # create thread and move to it
        self.thread = QtCore.QThread()
        self._quit = self.thread.quit
        self.start = self.thread.start
        self.running = self.thread.isRunning
        self.moveToThread(self.thread)
        self.thread.started.connect(self._on_start)

    @QtSlot()
    @catch_all
    def _on_start(self):
        super(QtThreadEventLoop, self).start()

    def join(self, timeout=3600):
        """Wait until the event loop terminates or ``timeout`` is
        reached.

        :keyword float timeout: timeout in seconds.

        """
        self.thread.wait(int(timeout * 1000))


class ComponentRunner(ComponentRunnerBase):
    """Qt version of the
    :py:class:`pyctools.core.compound.ComponentRunner` component."""

    def __init__(self):
        if qt_version_info < (6, 0):
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_X11InitThreads)
        self.app = QtWidgets.QApplication(sys.argv)
        super(ComponentRunner, self).__init__()

    def do_loop(self, comp):
        execute(self.app)
