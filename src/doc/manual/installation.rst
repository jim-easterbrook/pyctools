.. Pyctools - a picture processing algorithm development kit.
   http://github.com/jim-easterbrook/pyctools
   Copyright (C) 2014-25  Pyctools contributors

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

Although Pyctools has been written for Linux computers, the cross-platform nature of Python means it can also be installed on Windows and (probably) MacOS computers.
(I've tested Windows installation on a virtual machine, but don't have a MacOS machine to test it with.)

Pyctools requires Python 3 and its package manager pip_.
These are probably already installed on Linux computers, but may need to be installed on Windows and MacOS.
Python installers can be downloaded from https://www.python.org/downloads/.

I strongly recommend using a Python `virtual environment`_ to install Pyctools.
This isolates your Pyctools setup from other Python software on your computer, preventing possible clashes over required versions of some dependencies.

After creating a virtual environment for Pyctools, activate it and update its copy of pip_:

.. tabs::
    .. code-tab:: none Linux/MacOS

        $ python3 -m venv --system-site-packages pyctools
        $ source pyctools/bin/activate
        (pyctools) $ python -m pip install -U pip
        Collecting pip
          Using cached pip-21.3.1-py3-none-any.whl (1.7 MB)
        Installing collected packages: pip
          Attempting uninstall: pip
            Found existing installation: pip 20.0.2
            Uninstalling pip-20.0.2:
              Successfully uninstalled pip-20.0.2
        Successfully installed pip-21.3.1

    .. code-tab:: none Windows

        C:\Users\Jim>py -m venv --system-site-packages pyctools

        C:\Users\Jim>pyctools\Scripts\activate

        (pyctools) C:\Users\Jim>python -m pip install -U pip
        Requirement already satisfied: pip in c:\users\jim\pyctools\lib\site-packages (21.1.1)
        Collecting pip
          Using cached pip-24.3.1-py3-none-any.whl (1.8 MB)
        Installing collected packages: pip
          Attempting uninstall: pip
            Found existing installation: pip 21.1.1
            Uninstalling pip-21.1.1:
              Successfully uninstalled pip-21.1.1
        Successfully installed pip-24.3.1

Note the use of ``--system-site-packages`` when creating the virtual environment.
This allows access to system wide Python packages, preventing unnecessary duplication in the virtual environment.

Now you can install Pyctools:

.. tabs::
    .. code-tab:: none Linux/MacOS

        (pyctools) $ pip install pyctools-core
        Collecting pyctools-core
          Downloading pyctools_core-0.7.0.tar.gz (396 kB)
             |████████████████████████████████| 396 kB 916 kB/s
          Installing build dependencies ... done
          Getting requirements to build wheel ... done
          Installing backend dependencies ... done
          Preparing metadata (pyproject.toml) ... done
        Requirement already satisfied: numpy<2 in /usr/lib64/python3.6/site-packages (from pyctools-core) (1.17.3)
        Collecting exiv2>=0.11
          Using cached exiv2-0.17.1-cp36-cp36m-manylinux_2_28_x86_64.whl (15.1 MB)
        Requirement already satisfied: pillow in /usr/lib64/python3.6/site-packages (from pyctools-core) (8.4.0)
        Requirement already satisfied: docutils in /usr/lib/python3.6/site-packages (from pyctools-core) (0.14)
        Building wheels for collected packages: pyctools-core
          Building wheel for pyctools-core (pyproject.toml) ... done
          Created wheel for pyctools-core: filename=pyctools.core-0.7.0-cp36-cp36m-linux_x86_64.whl size=621929 sha256=ed40977bab66c9ae1655f6a0766660542b8b2871a858c569fd5fe1dd25853a43
          Stored in directory: /home/jim/.cache/pip/wheels/2e/ed/d4/233ab864b806a264d7573d0f37ceeb6ac1adf08413c790dc97
        Successfully built pyctools-core
        Installing collected packages: exiv2, pyctools-core
        Successfully installed exiv2-0.17.1 pyctools-core-0.7.0

    .. code-tab:: none Windows

        (pyctools) C:\Users\Jim>pip install pyctools-core
        Collecting pyctools-core
          Downloading pyctools_core-0.7.0.tar.gz (396 kB)
          Installing build dependencies ... done
          Getting requirements to build wheel ... done
          Preparing metadata (pyproject.toml) ... done
        Collecting docutils (from pyctools-core)
          Downloading docutils-0.20.1-py3-none-any.whl.metadata (2.8 kB)
        Collecting exiv2>=0.11 (from pyctools-core)
          Downloading exiv2-0.17.1-cp38-cp38-win_amd64.whl.metadata (7.3 kB)
        Collecting numpy<2 (from pyctools-core)
          Using cached numpy-1.24.4-cp38-cp38-win_amd64.whl.metadata (5.6 kB)
        Collecting pillow (from pyctools-core)
          Downloading pillow-10.4.0-cp38-cp38-win_amd64.whl.metadata (9.3 kB)
        Downloading exiv2-0.17.1-cp38-cp38-win_amd64.whl (8.5 MB)
           ---------------------------------------- 8.5/8.5 MB 759.9 kB/s eta 0:00:00
        Using cached numpy-1.24.4-cp38-cp38-win_amd64.whl (14.9 MB)
        Downloading docutils-0.20.1-py3-none-any.whl (572 kB)
           -------------------------------------- 572.7/572.7 kB 537.2 kB/s eta 0:00:00
        Downloading pillow-10.4.0-cp38-cp38-win_amd64.whl (2.6 MB)
           ---------------------------------------- 2.6/2.6 MB 643.4 kB/s eta 0:00:00
        Building wheels for collected packages: pyctools-core
          Building wheel for pyctools-core (pyproject.toml) ... done
          Created wheel for pyctools-core: filename=pyctools.core-0.7.0-cp38-cp38-win_amd64.whl size=584730 sha256=1a95bd055efa92d23cff0504e8f149e61090c050e49e8c762d22f011c1bb0896
          Stored in directory: c:\users\jim\appdata\local\pip\cache\wheels\20\a8\27\ded5e99bc4659417a1489238c2d7459b6055ba724ed0bd4d1c
        Successfully built pyctools-core
        Installing collected packages: exiv2, pillow, numpy, docutils, pyctools-core
        Successfully installed docutils-0.20.1 exiv2-0.17.1 numpy-1.24.4 pillow-10.4.0 pyctools-core-0.7.0

Note that the ``pyctools-core`` package is compiled during installation.
This is because it contains some components that aren't pure Python.
Compiling these components from "C" enables them to run much faster.

On Windows you may get an error message like "Microsoft Visual C++ 14.0 or greater is required."
Fortunately MicroSoft provide a free compiler which you can download from https://visualstudio.microsoft.com/visual-cpp-build-tools/.
Select the "Desktop development with C++" option in the Visual Studio Installer.

After you have successfully installed Pyctools you can test it by running the :py:mod:`pyctools-editor <pyctools.tools.editor>` GUI.
If you get a "ModuleNotFoundError: No module named 'PyQt5'" error then you need to install one of ``PyQt5``, ``PyQt6``, ``PySide2``, or ``PySide6``, e.g. ``pip install pyqt6``.
(Note that pip package names are case insensitive.)

Pyctools has several optional dependencies that provide extra features as detailed below.

Dependencies
------------

On Linux these dependencies can usually be installed with the distribution's package manager application.
Most are also available from the `Python Package Index (PyPI)`_.
These will often be newer versions.
The ``pip`` command should be used to install packages from PyPI.
Do not run ``pip`` as root (e.g. with ``sudo``) as this may corrupt your operating system.
If you are not using a virtual environment then use ``pip install --user`` to install in your local user directory.

`NumPy <http://www.numpy.org/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If NumPy is already installed, the command ``python3 -c 'import numpy'`` should run without error.

NumPy should be installable with a Linux system's package manager.
Be sure to get the "development headers" version (probably has ``-dev`` or ``-devel`` in the name) to allow Cython extensions that use NumPy to be compiled.
Alternatively it can be installed with ``pip``::

  pip3 install --user -U numpy

(The ``-U`` option will upgrade any existing installation.)

`python-exiv2 <https://pypi.org/project/exiv2/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``pip`` to install python-exiv2::

  pip3 install --user -U exiv2

`OpenCV <http://opencv.org/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenCV is an optional dependency.
If it is not installed then some Pyctools components will not be usable.

If OpenCV is already installed the ``python3 -c 'import cv2'`` command will run without error.

OpenCV should be installable with a Linux system's package manager.
You need to install the Python bindings as well as the core library.

`FFmpeg <https://www.ffmpeg.org/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

FFmpeg is used to read and write video files.
If you are only interested in still image processing then it is not required.

The ``ffmpeg -h`` command will show if FFmpeg is already installed.

FFmpeg should be installable with a Linux system's package manager.
Installing it on Windows is not so easy.

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

PyQt_ or PySide_
^^^^^^^^^^^^^^^^

The :py:mod:`Pyctools visual editor <pyctools.tools.editor>` uses the Qt graphics system via a Python package.
Pyctools can use any one of ``PyQt5``, ``PyQt6``, ``PySide2``, or ``PySide6``.

At least one of these should be installable with your system's package manager.

`PyOpenGL <http://pyopengl.sourceforge.net/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

PyOpenGL is an optional dependency.
If it is not installed then the :py:mod:`pyctools.components.qt.qtdisplay` component will not be usable.

If PyOpenGL is already installed the ``python3 -c 'import OpenGL'`` command will run without error.

PyOpenGL should be installable with a Linux system's package manager.
It may be called ``python-opengl`` or similar.

`pillow <http://python-pillow.github.io/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The easiest way to install pillow is with ``pip``::

  pip3 install --user pillow

Pyctools core
-------------

Although Pyctools can be installed from PyPI_, it may be better to clone the GitHub repo.
Cloning the repo makes it easy to keep up to date with a ``git pull`` command.

Clone the repo and install Pyctools as follows::

  git clone https://github.com/jim-easterbrook/pyctools.git
  cd pyctools
  pip3 install --user .

You can easily install most of the dependencies at the same time with ``pip3 install --user .[all]``.

Documentation
^^^^^^^^^^^^^

Pyctools documentation is available `online <https://pyctools.readthedocs.io/>`_ but it's sometimes useful to have a local copy.
A local copy may be more up to date and should include documentation of all your installed components, not just the core Pyctools ones.
The documentation is built using a package called `Sphinx <https://sphinx-doc.org/>`_, available from PyPI::

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


.. _pip: https://pip.pypa.io/en/stable/getting-started/
.. _PyPI: https://pypi.org/
.. _PyQt: https://riverbankcomputing.com/software/pyqt/intro
.. _PySide: https://wiki.qt.io/Qt_for_Python
.. _Python Package Index (PyPI): https://pypi.org/
.. _virtual environment: https://docs.python.org/3/library/venv.html
