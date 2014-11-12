.. Pyctools - a picture processing algorithm development kit.
   http://github.com/jim-easterbrook/pyctools
   Copyright (C) 2014  Jim Easterbrook  jim@jim-easterbrook.me.uk

   This program is free software: you can redistribute it and/or
   modify it under the terms of the GNU General Public License as
   published by the Free Software Foundation, either version 3 of the
   License, or (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see
   <http://www.gnu.org/licenses/>.

Introduction
============

Pyctools is a collection of picture processing primitive components that you can easily interconnect to make complex algorithm simulations.
The components can be used directly in Python scripts but there is also an easy to use visual editor.

.. image:: /images/editor_8.png

Background
----------

A lot of my work at `BBC R&D <http://www.bbc.co.uk/rd>`_ involved experimenting with different picture processing algorithms.
My colleagues and I developed a set of programs we called "pictools".
These implemented simple primitives such as scaling an image, but could be connected together to do more complex tasks.
They used shell pipelines to pass picture data between them, giving some of the benefits of parallel processing.
Despite this they were still quite slow to run, with overnight or weekend processing still required to produce a useful amount of video from a complex system such as the `Transform PAL Decoder <http://www.jim-easterbrook.me.uk/pal/>`_.

In a more recent `project at BBC R&D <http://www.bbc.co.uk/rd/publications/whitepaper191>`_ I implemented some real-time video processing in a similarly flexible manner.
This used `Kamaelia <http://www.kamaelia.org/>`_ to connect simple components together, with the advantage of dynamic connections, e.g. to monitor an existing recording process.

Pyctools draws on both of these.
The intention is to develop a set of simple components that can easily be interconnected to make complex systems.

Technologies
------------

There are several options for software frameworks to create interconnected components.
My previous experience with `Kamaelia <http://www.kamaelia.org/>`_ was very positive so when I discovered that its author (a former colleague) was developing a simpler replacement called `Guild <https://github.com/sparkslabs/guild>`_ it seemed an obvious choice.

Python's `NumPy <http://www.numpy.org/>`_ library provides an array object that is ideally suited to image processing.
`OpenCV <http://opencv.org/>`_ has Python bindings that use NumPy arrays and provide a huge range of image processing functions.
Pyctools makes it easy to encapsulate OpenCV (and other library) functions in components that can be easily interconnected.

If a function isn't available from one of these libraries it is quite easy to write one using `Cython <http://cython.org/>`_.
This Python-like compiled language can run much faster than pure Python.
For example, the :py:mod:`Resize <pyctools.components.interp.resize>` component can resize an image using a user supplied filter -- something that NumPy and OpenCV can't do (as far as I can tell).
I initially wrote it in Python, to prove my algorithm worked, then moved the core function into a Cython module.

Metadata
^^^^^^^^

One of the better features of the BBC pictools was the "audit trail".
Every tool extended this block of text with details of what it did - the program name, its parameters, the time and machine it ran on, etc.
This often proved useful when seeking to find out what a particular file was supposed to be.

Pyctools uses XMP "sidecar" files to store metadata like this.
Using sidecar files means we won't need to restrict the video or still image file formats to those that support metadata.
`PyGObject <https://wiki.gnome.org/Projects/PyGObject>`_ and `gexiv2 <https://wiki.gnome.org/Projects/gexiv2>`_ are used to read and write these metadata files.

Extensibility
^^^^^^^^^^^^^

Python provides "namespace packages" that allow a package to be split across several files.
This feature appears to be little known (and not very well documented) but the key point is that you can have two or more software packages (e.g. "pyctools.core" and "pyctools.pal") installed in different places (e.g. system-wide and local/personal "site-packages" directories) that both provide parts of a single package, "pyctools".
For example, you can write code like this::

  from pyctools.components.io.videofilereader import VideoFileReader
  from pyctools.components.pal.common import To4Fsc

and not be aware that those two components are imported from totally separate sources.

This makes it easy to mix Pyctools core components with locally written ones specific to your own application.
Companies can develop their own proprietary Pyctools for internal use or can publish them for wider use without having to make them part of a larger open source project.