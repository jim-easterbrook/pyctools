Pyctools
========

A picture processing algorithm development kit.

Pyctools is a collection of picture processing primitive components that you can easily interconnect to make complex algorithm simulations.
It works with stills or video, and utilises popular libraries such as `Python Imaging Library`_, NumPy_ and OpenCV_.

.. image:: https://pyctools.readthedocs.io/en/latest/_images/editor_8.png

Example projects using pyctools include `pyctools-pal`_ (a simulation of the `Transform PAL decoder`_) and `pyctools-demo`_ (demonstrations of some simple processing).

Documentation
-------------

The core Pyctools library and components are documented on `Read The Docs`_.
If you install additional components you should build a local copy of the documentation to include the extra components.

Requirements
------------

Essential
^^^^^^^^^

* Python_ version 3.6 or later.
* NumPy_ for its powerful multi-dimensional array object.
* `Python Imaging Library`_ for image file reading and writing. (The pillow_ fork of PIL is recommended.)
* Cython_ to build fast extensions for Python.
* `python-exiv2`_ to handle metadata.

Optional
^^^^^^^^

* OpenCV_ python bindings for advanced image processing.
* FFmpeg_ to read and write video files.
* rawkit_ and/or rawpy_ to read raw image files.
* PyQt_ (or PySide_) and PyOpenGL_ graphic toolkit used by the Pyctools visual editor and the Qt display components.
* Sphinx_ to build local documentation.

Installation
------------

Please see `the documentation`_ for full details of how to install Pyctools and its requirements.

Licence
-------

| Pyctools - a picture processing algorithm development kit.
| https://github.com/jim-easterbrook/pyctools
| Copyright (C) 2014-25  Pyctools contributors

Pyctools is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

Pyctools is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with Pyctools.  If not, see https://www.gnu.org/licenses/.


.. _Cython: https://cython.org/
.. _FFmpeg: https://www.ffmpeg.org/
.. _NumPy: https://numpy.org/
.. _OpenCV: https://opencv.org/
.. _pillow: https://python-pillow.org/
.. _pyctools-demo: https://github.com/jim-easterbrook/pyctools-demo
.. _pyctools-pal: https://github.com/jim-easterbrook/pyctools-pal
.. _PyOpenGL: https://pyopengl.sourceforge.net/
.. _PyQt: https://riverbankcomputing.com/software/pyqt/intro
.. _PySide: https://wiki.qt.io/Qt_for_Python
.. _Python: https://www.python.org/
.. _python-exiv2: https://pypi.org/project/exiv2/
.. _Python Imaging Library:
    https://en.wikipedia.org/wiki/Python_Imaging_Library
.. _rawkit: https://rawkit.readthedocs.io/
.. _rawpy: https://letmaik.github.io/rawpy/api/index.html
.. _Read The Docs: https://pyctools.readthedocs.io/
.. _Sphinx: https://www.sphinx-doc.org/
.. _the documentation:
    https://pyctools.readthedocs.io/en/latest/manual/installation.html
.. _Transform PAL decoder: https://www.jim-easterbrook.me.uk/pal/
