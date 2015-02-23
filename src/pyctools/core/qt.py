#  Pyctools - a picture processing algorithm development kit.
#  http://github.com/jim-easterbrook/pyctools
#  Copyright (C) 2015  Pyctools contributors
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

"""Qt event loops.

.. autosummary::

   QtEventLoop
   QtThreadEventLoop

"""

__all__ = ['QtEventLoop', 'QtThreadEventLoop']
__docformat__ = 'restructuredtext en'

from PyQt4 import QtCore

# create unique event type
_queue_event = QtCore.QEvent.registerEventType()

class ActionEvent(QtCore.QEvent):
    def __init__(self, command):
        super(ActionEvent, self).__init__(_queue_event)
        self.command = command


class CoreEventLoop(QtCore.QObject):
    def event(self, event):
        if event.type() != _queue_event:
            return super(CoreEventLoop, self).event(event)
        event.accept()
        if event.command is None:
            self.owner.stop_event()
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

    def stop(self):
        if self.running():
            self._put_on_queue(None)

    def new_frame(self):
        self._put_on_queue(self.owner.new_frame_event)

    def new_config(self):
        self._put_on_queue(self.owner.new_config_event)


class QtEventLoop(CoreEventLoop):
    def __init__(self, owner):
        super(QtEventLoop, self).__init__()
        self.owner = owner
        self.is_running = False

    def _quit(self):
        self.is_running = False

    def start(self):
        self.is_running = True
        self.owner.start_event()

    def join(self):
        pass

    def running(self):
        return self.is_running


class QtThreadEventLoop(CoreEventLoop):
    def __init__(self, owner):
        super(QtThreadEventLoop, self).__init__()
        self.owner = owner
        # create thread and move to it
        self.thread = QtCore.QThread()
        self._quit = self.thread.quit
        self.start = self.thread.start
        self.join = self.thread.wait
        self.running = self.thread.isRunning
        self.moveToThread(self.thread)
        self.thread.started.connect(self.owner.start_event)
