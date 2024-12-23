.. Pyctools - a picture processing algorithm development kit.
   http://github.com/jim-easterbrook/pyctools
   Copyright (C) 2014-24  Pyctools contributors

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

Writing components
==================

.. epigraph::

   A successful tool is one that was used to do something undreamt of by its author.

   -- Stephen C. Johnson

It is unlikely that you will be able to do everything you want to do with Pyctools "out of the box".
Sooner or later you will find that there isn't a component for an image processing operation you need to solve your problem.
The solution is to extend Pyctools by writing a new component.

Preliminaries
-------------

Integrating your new component(s) into a Pyctools installation will be easier if you set up your build environment as described below.
The Pyctools source files include example files to help with this.

Namespaces
^^^^^^^^^^

Python `namespace packages`_ allow multiple distribution packages to share a package hierarchy.
For example, the `pyctools.core`_ and `pyctools.pal`_ distribution packages both install Pyctools components in the ``pyctools.components`` package.

When you write your components you should follow a similar naming structure and make them part of the ``pyctools.components`` hierarchy.
This will ensure that they are included in the component list shown in the :py:mod:`pyctools-editor <pyctools.tools.editor>` visual editor.

Choosing a name
^^^^^^^^^^^^^^^

This is well known to be one of the most important parts of software writing.
If your new component fits the existing Pyctools component hierarchy then it makes a lot of sense to add it to an existing package.
For example, if you're writing a component to read a common file type you should probably add it to ``pyctools.components.io``.

Alternatively you may prefer to group all your components under one package.
Perhaps you work for a company that wants to make its ownership explicit.
In this case you might want to add your new file reader to ``pyctools.components.bigcorp.io``.
(Substitute your company name for ``bigcorp``, but keep it lower case. All Python packages and modules should have lower case names.)

There is just one golden rule -- don't use a (complete) module name that's already in use.
For example, don't use ``pyctools.components.io.videofilereader``.
Consider ``pyctools.components.bigcorp.io.videofilereader`` or ``pyctools.components.io.foofilereader`` instead.

Build environment
^^^^^^^^^^^^^^^^^

The easiest way to get started is to copy the ``examples/simple`` directory, edit the ``pyproject.toml`` file and try building and installing.
If this works you should have a new ``Flip`` component available in the :py:mod:`pyctools-editor <pyctools.tools.editor>` program.
The ``examples/simple/test_flip.py`` script demonstrates the effect of the ``Flip`` component.

Having successfully set up your build environment you are ready to start writing your new component.

"Transformer" components
------------------------

The most common Pyctools components have one input and one output.
They do nothing until a frame is received, then they "transform" that input frame into an output frame and send it to their output.
Pyctools provides a :py:class:`~pyctools.core.base.Transformer` base class to make it easier to write transformer components.

Consider the ``Flip`` example component.
This listing shows all the active Python code:

.. literalinclude:: ../../../examples/simple/src/pyctools/components/example/flip.py
   :language: python
   :linenos:
   :lines: 24, 26-

Line 1 is important.
The module's ``__all__`` value is used by :py:mod:`pyctools-editor <pyctools.tools.editor>` to determine what components a module provides.

The :py:meth:`~pyctools.core.base.Component.initialise` method (lines 9-10) is called by the component's constructor.
It is here that you add any configuration values that your component uses.

The main part of the component is the :py:meth:`~pyctools.core.base.Transformer.transform` method (lines 12-25).
This is called each time there is some work to do, i.e. an input frame has arrived and an output frame is available from the :py:class:`~pyctools.core.base.ObjectPool`.

A component's configuration can be changed while it is running.
This is done via a threadsafe queue.
The :py:meth:`~pyctools.core.config.ConfigMixin.update_config` method (line 13) gets any new configuration values from the queue so each time the component does any work it is using the most up-to-date config.

The ``out_frame`` result is already initialised with a copy of the ``in_frame``'s metadata and a link to its image data.
The :py:meth:`in_frame.as_PIL() <pyctools.core.frame.Frame.as_PIL>` call (line 19) gets the input image data as a :py:mod:`PIL:PIL.Image` object, converting it if necessary.
(The frame's :py:meth:`~pyctools.core.frame.Frame.as_numpy` method could be used to get numpy data instead.)

Line 20 sets the output frame data to a new PIL image.
Note that you must never modify the input frame's data.
Because of the parallel nature of Pyctools that same input frame may also be used by another component.

Finally lines 21-24 add some text to the output frame's "audit trail" metadata and line 25 returns ``True`` to indicate that processing was successful.

"Passthrough" components
^^^^^^^^^^^^^^^^^^^^^^^^

Components that don't appear to need an output (e.g. a video display or file writer) are usually implemented as "passthrough" components -- the input data is passed straight through to the output.
This conveniently allows a stream of frames to be simultaneously saved in a file and displayed in a window by pipelining a :py:mod:`VideoFileWriter <pyctools.components.io.videofilewriter>` with a :py:mod:`QtDisplay <pyctools.components.qt.qtdisplay>` component.

The passthrough component's ``transform`` method saves or displays the input frame, but need not do anything else.
The base class takes care of creating the output frame correctly.

Source components
-----------------

Components such as file readers have an output but no inputs.
They use the :py:class:`~pyctools.core.base.Component` base class directly.
In most cases they use an output frame pool and generate a new frame each time a frame object is available from the pool.
See the :py:mod:`ZonePlateGenerator <pyctools.components.zone.zoneplategenerator>` source code for an example.

Namespace packages and ``__init__.py`` files
--------------------------------------------

There is some confusing advice about including ``__init__.py`` files in namespace packages.
In general, don't do this.
If two "distribution packages" both have ``__init__.py`` in the same sub-package (e.g. ``pyctools.components.io``) then uninstalling either package will remove ``__init__.py``.
If you add a unique sub-package (e.g. ``pyctools.components.bigcorp``) then you can include a ``__init__.py`` file.
It should probably do nothing more than provide a docstring for the sub-package.


.. _namespace packages: https://packaging.python.org/en/latest/guides/packaging-namespace-packages/
.. _pyctools.core: https://github.com/jim-easterbrook/pyctools
.. _pyctools.pal: https://github.com/jim-easterbrook/pyctools-pal
