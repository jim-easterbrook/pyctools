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

from collections import namedtuple

from PyQt5 import QtCore

qt_version_info = namedtuple(
    'qt_version_info', ('major', 'minor', 'micro'))._make(
        map(int, QtCore.QT_VERSION_STR.split('.')))

# create unique event type
_queue_event = QtCore.QEvent.registerEventType()

class ActionEvent(QtCore.QEvent):
    def __init__(self, command, **kwds):
        super(ActionEvent, self).__init__(_queue_event, **kwds)
        self.command = command


class CoreEventLoop(QtCore.QObject):
    def event(self, event):
        if event.type() != _queue_event:
            return super(CoreEventLoop, self).event(event)
        event.accept()
        if event.command is None:
            try:
                self.owner.stop_event()
            except Exception as ex:
                self.owner.logger.exception(ex)
            self._quit()
            return True
        try:
            event.command()
        except Exception as ex:
            self.owner.logger.exception(ex)
        return True

    def _put_on_queue(self, command):
        QtCore.QCoreApplication.postEvent(
            self, ActionEvent(command), QtCore.Qt.LowEventPriority)

    def start(self):
        try:
            self.owner.start_event()
        except Exception as ex:
            self.owner.logger.exception(ex)

    def stop(self):
        if self.running():
            self._put_on_queue(None)

    def new_frame(self):
        self._put_on_queue(self.owner.new_frame_event)

    def new_config(self):
        self._put_on_queue(self.owner.new_config_event)


class QtEventLoop(CoreEventLoop):
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
        self.owner = owner
        self.is_running = False

    def _quit(self):
        self.is_running = False

    def start(self):
        self.is_running = True
        super(QtEventLoop, self).start()

    def join(self):
        pass

    def running(self):
        return self.is_running


class QtThreadEventLoop(CoreEventLoop):
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

    """
    def __init__(self, owner, **kwds):
        super(QtThreadEventLoop, self).__init__(**kwds)
        self.owner = owner
        # create thread and move to it
        self.thread = QtCore.QThread()
        self._quit = self.thread.quit
        self.start = self.thread.start
        self.join = self.thread.wait
        self.running = self.thread.isRunning
        self.moveToThread(self.thread)
        self.thread.started.connect(self.start)
