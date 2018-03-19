#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2015-18  Pyctools contributors
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

__all__ = ['QtEventLoop', 'QtThreadEventLoop']
__docformat__ = 'restructuredtext en'

from collections import deque, namedtuple
import time

from PyQt5 import QtCore

from pyctools.core.base import BaseEventLoop

qt_version_info = namedtuple(
    'qt_version_info', ('major', 'minor', 'micro'))._make(
        map(int, QtCore.QT_VERSION_STR.split('.')))

# create unique event type
_queue_event = QtCore.QEvent.registerEventType()

class ActionEvent(QtCore.QEvent):
    def __init__(self, command, **kwds):
        super(ActionEvent, self).__init__(_queue_event, **kwds)
        self.command = command


class QtEventLoop(BaseEventLoop, QtCore.QObject):
    """Event loop using the Qt "main thread" (or "GUI thread").

    Use this event loop if your component is a Qt widget or needs to run
    in the main Qt thread for any other reason. See the
    :py:mod:`~pyctools.components.qt.qtdisplay.QtDisplay` component for
    an example.

    Pyctools event loops are described in more detail in the
    :py:class:`~.base.ThreadEventLoop` documentation.

    .. automethod:: stop()

    """
    def __init__(self, **kwds):
        super(QtEventLoop, self).__init__(**kwds)
        self._running = False
        self._incoming = deque()

    def event(self, event):
        if event.type() != _queue_event:
            return super(QtEventLoop, self).event(event)
        event.accept()
        if not self._do_command(event.command):
            self._running = False
            self._quit()
        return True

    def _put_on_queue(self, command):
        if self._running:
            # queue event normally
            QtCore.QCoreApplication.postEvent(
                self, ActionEvent(command), QtCore.Qt.LowEventPriority)
        else:
            # save event until we are started
            self._incoming.append(command)

    def _quit(self):
        pass

    def start(self):
        if self._running:
            raise RuntimeError('Component {} is already running'.format(
                self.owner.__class__.__name__))
        self._running = True
        self._put_on_queue(self._do_start)
        # process any events that arrived before we started
        while self._incoming:
            self._put_on_queue(self._incoming.popleft())

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

    .. automethod:: start()

    .. automethod:: stop()

    .. automethod:: running()

    """
    def __init__(self, owner, **kwds):
        super(QtThreadEventLoop, self).__init__(owner=owner, **kwds)
        # create thread and move to it
        self.thread = QtCore.QThread()
        self._quit = self.thread.quit
        self.start = self.thread.start
        self.running = self.thread.isRunning
        self.moveToThread(self.thread)
        self.thread.started.connect(self._on_start)

    @QtCore.pyqtSlot()
    def _on_start(self):
        super(QtThreadEventLoop, self).start()

    def join(self, timeout=3600):
        """Wait until the event loop terminates or ``timeout`` is
        reached.

        :keyword float timeout: timeout in seconds.

        """
        self.thread.wait(int(timeout * 1000))
