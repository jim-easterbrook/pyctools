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
The components can be used in Python scripts but there is also an easy to use visual editor.

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

Python's `NumPy <http://www.numpy.org/>`_ library provides an array object that is ideally suited to image processing.
`OpenCV <http://opencv.org/>`_ has Python bindings that use NumPy arrays and provide a huge range of image processing functions.
Pyctools makes it easy to encapsulate OpenCV (and other library) functions in components that can be easily interconnected.

If a function isn't available from one of these libraries it is quite easy to write one using `Cython <http://cython.org/>`_.
This Python-like compiled language can run much faster than pure Python.
For example, the :py:mod:`Resize <pyctools.components.interp.resize>` component can resize an image using a user supplied filter -- something that NumPy and OpenCV can't do (as far as I could tell).
I initially wrote it in Python, to prove my algorithm worked, then moved the core function into a Cython module.