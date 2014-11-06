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

"""Transformer base class.

A Transformer is a Pyctools :py:class:`~.component.Component` that has
one input and one output. When an input :py:class:`~.frame.Frame`
object is received, and an output :py:class:`~.frame.Frame` object is
available from a pool, the ":py:meth:`~Transformer.transform`" method
is called to do the component's actual work.

"""

__all__ = ['Transformer']
__docformat__ = 'restructuredtext en'

from collections import deque

from guild.actor import *

from .component import Component

class Transformer(Component):
    with_outframe_pool = True

    def __init__(self, **kw):
        self._transformer_in_frames = deque()
        self._transformer_out_frames = deque()
        self._transformer_ready = True
        super(Transformer, self).__init__(**kw)

    def set_ready(self, value):
        """Defer processing until some condition is met.

        Call this from your component's constructor or
        :py:meth:`~.component.Component.initialise` method (with
        ``value`` set to ``False``) if you want to delay calls to
        :py:meth:`transform` until something else happens, such as the
        delivery of a filter in the
        :py:class:`~pyctools.components.interp.resize.Resize`
        component.

        :param bool value: Set to ``True`` if your component is ready
            to process.

        """
        self._transformer_ready = value
        self._transformer_transform()

    @actor_method
    def input(self, frame):
        """input(frame)

        Receive an input :py:class:`~.frame.Frame` from another
        :py:class:`~.component.Component`.

        """
        self._transformer_in_frames.append(frame)
        self._transformer_transform()

    @actor_method
    def new_out_frame(self, frame):
        """new_out_frame(frame)

        Receive an output :py:class:`~.frame.Frame` from the
        :py:class:`Transformer`'s :py:class:`~.objectpool.ObjectPool`.

        """
        self._transformer_out_frames.append(frame)
        self._transformer_transform()

    def _transformer_transform(self):
        while (self._transformer_ready and
               self._transformer_out_frames and self._transformer_in_frames):
            in_frame = self._transformer_in_frames.popleft()
            if not in_frame:
                self.output(None)
                self.stop()
                return
            out_frame = self._transformer_out_frames.popleft()
            out_frame.initialise(in_frame)
            if self.transform(in_frame, out_frame):
                self.output(out_frame)
            else:
                self.output(None)
                self.stop()

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
