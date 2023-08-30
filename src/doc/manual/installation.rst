.. Pyctools - a picture processing algorithm development kit.
   http://github.com/jim-easterbrook/pyctools
   Copyright (C) 2014-23  Pyctools contributors

   This file is part of Pyctools.

   Pyctools is free software: you can redistribute it and/or
   modify it under the terms of the GNU General Public License as
   published by the Free Software Foundation, either version 3 of the
   License, or (at your option) any later version.

   Pyctools is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with Pyctools.  If not, see <http://www.gnu.org/licenses/>.

Installation
============

Dependencies
------------

At first sight there are rather a lot of dependencies to be installed before using Pyctools.
However, many of these are likely to be already installed if you have a reasonably current Linux distribution installed on your computer.

Unless otherwise noted you should probably install the dependencies with your Linux distribution's package manager application.

Some packages are also available from the `Python Package Index (PyPI) <https://pypi.python.org/>`_.
These will often be newer versions.
The ``pip`` command should be used to install packages from PyPI.

`Python <https://www.python.org/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can test which version of Python is installed on your system with ``python3 --version``.
Any version from 3.5 onwards is suitable.

`NumPy <http://www.numpy.org/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If NumPy is already installed, the command ``python3 -c 'import numpy'`` should run without error.

NumPy should be installable with your system's package manager.
Be sure to get the "development headers" version (probably has ``-dev`` or ``-devel`` in the name) to allow Cython extensions that use NumPy to be compiled.
Alternatively it can be installed with ``pip``::

  pip3 install --user -U numpy

(The ``-U`` option will upgrade any existing installation.)

`Cython <http://cython.org/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``cython --version`` command will show if Cython is already installed.
Pyctools has been tested with version 0.19.1, but newer versions should work.

Cython should be installable with your system's package manager.
Alternatively it can be installed with ``pip``::

  pip3 install --user -U cython

`python-exiv2 <https://pypi.org/project/exiv2/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``pip`` to install python-exiv2::

  pip3 install --user -U exiv2

`OpenCV <http://opencv.org/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenCV is an optional dependency.
If it is not installed then some Pyctools components will not be usable.

If OpenCV is already installed the ``python3 -c 'import cv2'`` command will run without error.

OpenCV should be installable with your system's package manager.
You need to install the Python bindings as well as the core library.

`FFmpeg <https://www.ffmpeg.org/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

FFmpeg is possibly an optional dependency.
If it is not installed then the video file reading and writing components will not be usable.
I think these would be considered essential by most users!

The ``ffmpeg -h`` command will show if FFmpeg is already installed.

FFmpeg should be installable with your system's package manager.

`rawkit <https://rawkit.readthedocs.io/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :py:mod:`pyctools.components.io.rawimagefilereader` component uses ``rawkit`` to read raw image files such as the CR2 format produced by Canon cameras.
If you need to process raw images you can install ``rawkit`` using ``pip``::

  pip3 install --user rawkit

`rawpy <https://letmaik.github.io/rawpy/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :py:mod:`pyctools.components.io.rawimagefilereader2` component uses ``rawpy`` to read raw image files such as the CR2 format produced by Canon cameras.
If you need to process raw images you can install ``rawpy`` using ``pip``::

  pip3 install --user rawpy

`PyQt5 <https://riverbankcomputing.com/software/pyqt/intro>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

PyQt5 is an optional dependency.
If it is not installed then the :py:mod:`Pyctools visual editor <pyctools.tools.editor>` will not be usable.

If PyQt5 is already installed the ``python3 -c 'import PyQt5'`` command will run without error.

PyQt5 should be installable with your system's package manager.

`PyOpenGL <http://pyopengl.sourceforge.net/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

PyOpenGL is an optional dependency.
If it is not installed then the :py:mod:`pyctools.components.qt.qtdisplay` component will not be usable.

If PyOpenGL is already installed the ``python3 -c 'import OpenGL'`` command will run without error.

PyOpenGL should be installable with your system's package manager.
It may be called ``python-opengl`` or similar.

`pillow <http://python-pillow.github.io/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The easiest way to install pillow is with ``pip``::

  pip3 install --user pillow

Pyctools core
-------------

Although ``pip`` can be used to install Pyctools, it is better to clone the GitHub repos.
The project is still quite young and a lot of changes are being made.
Cloning the repos makes it easy to keep up to date with a ``git pull`` command.

Clone the repos and install Pyctools as follows::

  git clone https://github.com/jim-easterbrook/pyctools.git
  cd pyctools
  pip3 install --user .

Documentation
^^^^^^^^^^^^^

Pyctools documentation is available `online <http://pyctools.readthedocs.io/>`_ but it's sometimes useful to have a local copy.
A local copy may be more up to date and should include documentation of all your installed components, not just the core Pyctools ones.
The documentation is built using a package called `Sphinx <http://sphinx-doc.org/>`_, available from PyPI::

  pip3 install --user Sphinx

Having installed Sphinx you can use ``utils/build_docs.py`` to build the documentation::

  cd pyctools
  python3 utils/build_docs.py

The documentation can be read with any web browser.
The start page is ``doc/html/index.html``.

Pyctools extras
---------------

It is hoped that there will be an increasing number of extra Pyctools packages to expand the range of components available.
So far I've written a PAL coder / decoder simulation package and a package of extra components that probably aren't general enough to include in the core distribution.
These packages also demonstrate how Pyctools can be extended.
They are installed in the usual way::

  git clone https://github.com/jim-easterbrook/pyctools-pal.git
  cd pyctools-pal
  pip3 install --user .

::

  git clone https://github.com/jim-easterbrook/pyctools-jim.git
  cd pyctools-jim
  pip3 install --user .
