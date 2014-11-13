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

You can test which version of Python is installed on your system with ``python --version``.
Any version from 2.7 onwards is suitable, but note that OpenCV has not yet released a version with Python 3 support.

`Guild <https://github.com/sparkslabs/guild>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This currently needs to be downloaded from GitHub and installed with ``setup.py``.
You can download a ZIP archive from GitHub, but I prefer to use ``git`` to clone the repos::

  git clone https://github.com/sparkslabs/guild.git
  cd guild
  python setup.py build
  sudo python setup.py install

If you don't have root access on your machine (e.g. a corporate workstation), or want to install for yourself only, you can do a local installation with the ``--user`` option.
Replace the last line with::

  python setup.py install --user

`NumPy <http://www.numpy.org/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If NumPy is already installed, the command ``python -c 'import numpy'`` should run without error.

NumPy should be installable with your system's package manager.
Be sure to get the "development headers" version (probably has ``-dev`` or ``-devel`` in the name) to allow Cython extensions that use NumPy to be compiled.
Alternatively it can be installed with ``pip``::

  sudo pip install -U numpy

(The ``-U`` option will upgrade any existing installation.)

`Cython <http://cython.org/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``cython --version`` command will show if Cython is already installed.
Pyctools has been tested with version 0.19.1, but newer versions should work.

Cython should be installable with your system's package manager.
Alternatively it can be installed with ``pip``::

  sudo pip install -U cython

`GExiv2 <https://wiki.gnome.org/Projects/gexiv2>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If GExiv2 has been correctly installed, the command ``python -c 'from gi.repository import GObject, GExiv2'`` should run without error.

GExiv2 should be installable with your system's package manager.
You need to install the "introspection" bindings as well as the core library.
You may also need to install GObject and its introspection bindings.

`OpenCV <http://opencv.org/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenCV is an optional dependency.
If it is not installed then some Pyctools components will not be usable.

If OpenCV is already installed the ``python -c 'import cv2'`` command will run without error.

OpenCV should be installable with your system's package manager.
You need to install the Python bindings as well as the core library.

`FFmpeg <https://www.ffmpeg.org/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FFmpeg is possibly an optional dependency.
If it is not installed then the video file reading and writing components will not be usable.
I think these would be considered essential by most users!

The ``ffmpeg -h`` command will show if FFmpeg is already installed.

FFmpeg should be installable with your system's package manager.

`pillow <http://python-pillow.github.io/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The easiest way to install pillow is with ``pip``::

  sudo pip install pillow

or::

  pip install --user pillow

for a personal, non system-wide installation.

Pyctools core
-------------

Although ``pip`` can be used to install Pyctools, it is better to clone the GitHub repos.
The project is still quite young and a lot of changes are being made.
Cloning the repos makes it easy to keep up to date with a ``git pull`` command.

Clone the repos and install Pyctools as follows::

  git clone https://github.com/jim-easterbrook/pyctools.git
  cd pyctools
  python setup.py build
  sudo python setup.py install

As before, a "local" installation can be done instead of a system-wide installation::

  python setup.py install --user

Documentation
^^^^^^^^^^^^^

Pyctools documentation is available `online <https://pythonhosted.org/pyctools.core/>`_ but it's sometimes useful to have a local copy.
The documentation is built using a package called Sphinx, available from PyPI::

  sudo pip install Sphinx

Having installed Sphinx you can use ``setup.py`` to build the documentation::

  cd pyctools
  python setup.py build_sphinx

The documentation can be read with any web browser.
The start page is ``doc/html/index.html``.

Pyctools extras
---------------

It is hoped that there will be an increasing number of extra Pyctools packages to expand the range of components available.
At present there is only one -- a PAL coder / decoder simulation package that I've created to demonstrate how Pyctools can be extended.
It is installed in the usual way::

  git clone https://github.com/jim-easterbrook/pyctools-pal.git
  cd pyctools-pal
  python setup.py build
  sudo python setup.py install
