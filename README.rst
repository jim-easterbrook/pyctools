Pyctools
========

A picture processing algorithm development kit.

This is nothing more than a declaration of intent at present.
Eventually Pyctools will be a collection of picture processing primitive components that you can easily interconnect to make complex algorithm simulations.
It will work with stills or video, and utilise popular libraries such as `Python Imaging Library <http://www.pythonware.com/products/pil/>`_, `NumPy <http://www.numpy.org/>`_ and `OpenCV <http://opencv.org/>`_.

History
-------

A lot of my work at `BBC R&D <http://www.bbc.co.uk/rd>`_ involved experimenting with different picture processing algorithms.
My colleagues and I developed a set of programs we called "pictools".
These implemented simple primitives such as scaling an image, but could be connected together to do more complex tasks.
They used shell pipelines to pass picture data between them, giving some of the benefits of parallel processing.
Despite this they were still quite slow to run, with overnight or weekend processing still required to produce a useful amount of video from a complex system such as the `Transform PAL Decoder <http://www.jim-easterbrook.me.uk/pal/>`_.

In a more recent `project at BBC R&D <http://www.bbc.co.uk/rd/publications/whitepaper191>`_ I implemented some real-time video processing in a similarly flexible manner.
This used `Kamaelia <http://www.kamaelia.org/>`_ to connect simple components together, with the advantage of dynamic connections, e.g. to monitor an existing recording process.

Core technologies
-----------------

Pyctools will use `Guild <https://github.com/sparkslabs/guild>`_ at its core.
This is ideally suited to writing "reactive" components that do nothing until a video frame arrives on their input, then process the frame and (probably) send it to their output.
Guild makes it easy to interconnect such processes.

Although Pyctools will be written in Python this should not have any adverse impact on processing speeds.
All the computationally intensive work should be done in C/C++/Ada/whatever - as long as it can be interfaced to Python it can be used.
I'm hoping to be able to use a range of existing image processing libraries.

Pyctools will be primarily targeted at Python3.
I expect there will be some libraries that are only available in Python2 for a while yet, but I hope that situation won't last much longer.
My intention is to write Python3 that's compatible with Python2, not *vice versa*.

Pyctool components should be configurable in a consistent manner, using a tree of configuration objects that can be introspected.
This will allow development of a GUI to assemble networks of components that can then (optionally) be run as a batch script.

Metadata
--------

One of the better features of the BBC pictools was the "audit trail".
Every tool extended this block of text with details of what it did - the program name, its parameters, the time and machine it ran on, etc.
This often proved useful when seeking to find out what a particular file was supposed to be.

Pyctools will probably use XMP "sidecar" files to store metadata like this.
Using sidecar files means we won't need to restrict the video or still image file formats to those that support metadata.

Extensible
----------

The core parts of Pyctools will be open source and available from places such as `GitHub <https://github.com/>`_ and `PyPI <https://pypi.python.org/pypi>`_.
The intention is to structure it so that Pyctools extensions can be obtained from elsewhere and installed into a common Pyctools installation.
There should be nothing to stop commercial developers writing their own extensions, either for release or purely for internal use.

Licence
-------

| Pyctools - a picture processing algorithm development kit.
| http://github.com/jim-easterbrook/pyctools
| Copyright (C) 2014  Jim Easterbrook  jim@jim-easterbrook.me.uk

This program is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see http://www.gnu.org/licenses/.
