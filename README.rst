Pyctools
========

A picture processing algorithm development kit.

Pyctools is a collection of picture processing primitive components that you can easily interconnect to make complex algorithm simulations.
It works with stills or video, and utilises popular libraries such as `Python Imaging Library <http://www.pythonware.com/products/pil/>`_, `NumPy <http://www.numpy.org/>`_ and `OpenCV <http://opencv.org/>`_.

.. image:: https://pythonhosted.org/pyctools.core/_images/editor_8.png

Example projects using pyctools include `pyctools-pal <https://github.com/jim-easterbrook/pyctools-pal>`_ (a simulation of the `Transform PAL decoder <http://www.jim-easterbrook.me.uk/pal/>`_) and `pyctools-demo <https://github.com/jim-easterbrook/pyctools-demo>`_ (demonstrations of some simple processing).

Documentation
-------------

The core Pyctools library and components are documented on `ReadTheDocs.org <http://pyctools.readthedocs.org/>`_.
If you install additional components you should build a local copy of the documentation to include the extra components.

Requirements
------------

* `Python <https://www.python.org/>`_ version 2.7 or 3.x.
* `NumPy <http://www.numpy.org/>`_ for its powerful multi-dimensional array object.
* `Python Imaging Library <http://www.pythonware.com/products/pil/>`_ for image file reading and writing. (The `pillow <http://python-pillow.github.io/>`_ fork of PIL is recommended.)
* `Cython <http://cython.org/>`_ to build fast extensions for Python.
* `gexiv2 <https://wiki.gnome.org/Projects/gexiv2>`_ to handle metadata.
* `OpenCV <http://opencv.org/>`_ python bindings (optional) for advanced image processing.
* `FFmpeg <https://www.ffmpeg.org/>`_ (optional) to read and write video files.
* `rawkit <https://rawkit.readthedocs.org/>`_ (optional) to read raw image files.
* `PyQt <http://www.riverbankcomputing.com/software/pyqt/intro>`_ and `PyOpenGL <http://pyopengl.sourceforge.net/>`_ (optional) graphic toolkit used by the Pyctools visual editor and the Qt display components.
* `Sphinx <http://sphinx-doc.org/>`_ and `mock <https://github.com/testing-cabal/mock>`_ (optional) to build local documentation.

Installation
------------

Please see `the documentation <http://pyctools.readthedocs.org/en/latest/manual/installation.html>`_ for full details of how to install Pyctools and its requirements.

Licence
-------

| Pyctools - a picture processing algorithm development kit.
| http://github.com/jim-easterbrook/pyctools
| Copyright (C) 2014-16  Jim Easterbrook  jim@jim-easterbrook.me.uk

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
