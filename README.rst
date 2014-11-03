Pyctools
========

A picture processing algorithm development kit.

Pyctools is a collection of picture processing primitive components that you can easily interconnect to make complex algorithm simulations.
It works with stills or video, and utilises popular libraries such as `Python Imaging Library <http://www.pythonware.com/products/pil/>`_, `NumPy <http://www.numpy.org/>`_ and `OpenCV <http://opencv.org/>`_.

Requirements
------------

* `Python <https://www.python.org/>`_ version 2 or 3.
* `Guild <https://github.com/sparkslabs/guild>`_.
* `NumPy <http://www.numpy.org/>`_.
* `Python Imaging Library <http://www.pythonware.com/products/pil/>`_.
* `Cython <http://cython.org/>`_.

Installation
------------

The easiest way to install Pyctools is with `pip <https://pip.pypa.io/en/latest/>`_::

  sudo pip install pyctools.core

Note the use of ``sudo`` to install into system-wide directories.
If you don't have root access (e.g. on a corporate machine) you can create a local installation with the ``--user`` option::

  pip install --user pyctools.core

An alternative is to use a `virtual environment <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_.
(Although you probably need root access to install the ``virtualenv`` tool.)

If you want easy access to the pyctools source files (e.g. to write your own extensions) or want to use the latest development version you should clone the GitHub repository and use ``setup.py`` in the usual way::

  git clone https://github.com/jim-easterbrook/pyctools.git
  cd pyctools
  python setup.py build
  sudo python setup.py install

Documentation
-------------

The next thing on my todo list.

Background
----------

A lot of my work at `BBC R&D <http://www.bbc.co.uk/rd>`_ involved experimenting with different picture processing algorithms.
My colleagues and I developed a set of programs we called "pictools".
These implemented simple primitives such as scaling an image, but could be connected together to do more complex tasks.
They used shell pipelines to pass picture data between them, giving some of the benefits of parallel processing.
Despite this they were still quite slow to run, with overnight or weekend processing still required to produce a useful amount of video from a complex system such as the `Transform PAL Decoder <http://www.jim-easterbrook.me.uk/pal/>`_.

In a more recent `project at BBC R&D <http://www.bbc.co.uk/rd/publications/whitepaper191>`_ I implemented some real-time video processing in a similarly flexible manner.
This used `Kamaelia <http://www.kamaelia.org/>`_ to connect simple components together, with the advantage of dynamic connections, e.g. to monitor an existing recording process.

Core technologies
-----------------

Pyctools uses `Guild <https://github.com/sparkslabs/guild>`_ at its core.
This is ideally suited to writing "reactive" components that do nothing until a video frame arrives on their input, then process the frame and (probably) send it to their output.
Guild makes it easy to interconnect such processes.

Although Pyctools is written in Python this does not have any adverse impact on processing speeds.
All the computationally intensive work is done in Python extensions.
These can be written in a variety of languages, but I've found `Cython <http://cython.org/>`_ easiest to use.

Pyctools is primarily targeted at Python3.
There are some libraries that are only available in Python2 for a while yet, but I hope that situation won't last much longer.
My intention is to write Python3 that's compatible with Python2, not *vice versa*.

Metadata
--------

One of the better features of the BBC pictools was the "audit trail".
Every tool extended this block of text with details of what it did - the program name, its parameters, the time and machine it ran on, etc.
This often proved useful when seeking to find out what a particular file was supposed to be.

Pyctools uses XMP "sidecar" files to store metadata like this.
Using sidecar files means we won't need to restrict the video or still image file formats to those that support metadata.

Extensible
----------

The core parts of Pyctools are open source and available from `GitHub <https://github.com/jim-easterbrook/pyctools>`_ and `PyPI <https://pypi.python.org/pypi/pyctools.core/0.0.0>`_.
Python `namespace packages <http://legacy.python.org/dev/peps/pep-0420/>`_ are used (via `setuptools <https://pythonhosted.org/setuptools/setuptools.html#namespace-packages>`_) to allow Pyctools to be easily extended by other people.
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
