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

Python namespace packages allow the Python ``import`` statement to import modules in the same namespace hierarchy from different locations.
(Unfortunately they're complicated and still changing.
See `Python PEP 420 <https://www.python.org/dev/peps/pep-0420>`_.)
For example, if you have installed both `pyctools <https://github.com/jim-easterbrook/pyctools>`_ and `pyctools-pal <https://github.com/jim-easterbrook/pyctools-pal>`_ on your computer then you should have Pyctools components in two different directories::

   jim@Brains:~$ ls -l /usr/lib64/python2.7/site-packages/pyctools.core-0.1.2-py2.7-linux-x86_64.egg/pyctools/components/
   total 44
   -rw-r--r-- 1 root root 2098 Nov 18 08:58 arithmetic.py
   -rw-r--r-- 1 root root 2121 Nov 18 08:58 arithmetic.pyc
   drwxr-xr-x 2 root root 4096 Nov 18 08:58 colourspace
   -rw-r--r-- 1 root root  902 Nov 18 08:58 __init__.py
   -rw-r--r-- 1 root root  283 Nov 18 08:58 __init__.pyc
   drwxr-xr-x 2 root root 4096 Nov 18 08:58 interp
   drwxr-xr-x 2 root root 4096 Nov 18 08:58 io
   drwxr-xr-x 2 root root 4096 Nov 18 08:58 modulate
   drwxr-xr-x 2 root root 4096 Nov 18 08:58 plumbing
   drwxr-xr-x 2 root root 4096 Nov 18 08:58 qt
   drwxr-xr-x 2 root root 4096 Nov 18 08:58 zone
   jim@Brains:~$ ls -l /usr/lib/python2.7/site-packages/pyctools.pal-0.1.0-py2.7.egg/pyctools/components/
   total 12
   -rw-r--r-- 1 root root  902 Nov 12 14:48 __init__.py
   -rw-r--r-- 1 root root  267 Nov 12 14:48 __init__.pyc
   drwxr-xr-x 2 root root 4096 Nov 12 14:48 pal
   jim@Brains:~$ 

When a Python program imports from ``pyctools.components`` both these directories are searched for modules or subpackages.
The command ``import pyctools.components.io.videofilereader`` will use ``site-packages/pyctools.core`` whilst ``import pyctools.components.pal.decoder`` will use ``site-packages/pyctools.pal``.
The program user needn't know that the two ``import`` statements are using files from different installation packages.

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

The easiest way to get started is to copy the ``src/examples/simple`` directory, edit the ``setup.py`` file and try building and installing.
If this works you should have a new ``Flip`` component available in the :py:mod:`pyctools-editor <pyctools.tools.editor>` program.
The ``src/examples/simple/test_flip.py`` script demonstrates the effect of the ``Flip`` component.

Having successfully set up your build environment you are ready to start writing your new component.

"Transformer" components
------------------------

The most common Pyctools components have one input and one output.
They do nothing until a frame is received, then they "transform" that input frame into an output frame and send it to their output.
Pyctools provides a :py:class:`~pyctools.core.base.Transformer` base class to make it easier to write transformer components.

Consider the ``Flip`` example component.
This listing shows all the active Python code:

.. code-block:: python
   :linenos:

    __all__ = ['Flip']

    import PIL.Image

    from pyctools.core.base import Transformer
    from pyctools.core.config import ConfigEnum

    class Flip(Transformer):
        def initialise(self):
            self.config['direction'] = ConfigEnum(('vertical', 'horizontal'))

        def transform(self, in_frame, out_frame):
            self.update_config()
            direction = self.config['direction']
            if direction == 'vertical':
                flip = PIL.Image.FLIP_TOP_BOTTOM
            else:
                flip = PIL.Image.FLIP_LEFT_RIGHT
            in_data = in_frame.as_PIL()
            out_frame.data = in_data.transpose(flip)
            audit = out_frame.metadata.get('audit')
            audit += 'data = Flip(data)\n'
            audit += '    direction: %s\n' % direction
            out_frame.metadata.set('audit', audit)
            return True

Line 1 is important.
The module's ``__all__`` value is used by :py:mod:`pyctools-editor <pyctools.tools.editor>` to determine what components a module provides.

The ``initialise`` method (lines 9-10) is called by the component's constructor.
It is here that you add any configuration values that your component uses.

The main part of the component is the ``transform`` method (lines 12-25).
This is called each time there is some work to do, i.e. an input frame has arrived and an output frame is available from the :py:class:`~pyctools.core.base.ObjectPool`.

A component's configuration can be changed while it is running.
This is done via a threadsafe queue.
The ``update_config`` method (line 13) gets any new configuration values from the queue so each time the component does any work it is using the most up-to-date config.

The ``out_frame`` result is already initialised with a copy of the ``in_frame``'s metadata and a link to its image data.
Line 19 gets the input image data.
Because we're using a ``PIL.Image`` library method to transform the image data we use the ``in_frame.as_PIL`` method to convert the data to PIL format (if necessary).

Line 20 sets the output frame data to a new PIL image.
Note that you must never modify the input frame.
Because of the parallel nature of Pyctools that same input frame may also be used by another component.

Finally lines 21-24 add some text to the output frame's "audit trail" metadata and line 25 returns ``True`` to indicate that processing was successful.

"Passthrough" components
^^^^^^^^^^^^^^^^^^^^^^^^

Unlike some other image processing pipeline systems (such as Microsoft's `DirectShow <http://msdn.microsoft.com/en-us/library/windows/desktop/dd373390%28v=vs.85%29.aspx>`_) Pyctools doesn't have "sink" or "renderer" components that have an input but no output.
Instead a transformer component is used in "passthrough" mode -- the input data is passed straight through to the output.
This conveniently allows a stream of frames to be simultaneously saved in a file and displayed in a window by pipelining a :py:mod:`VideoFileWriter <pyctools.components.io.videofilewriter>` with a :py:mod:`QtDisplay <pyctools.components.qt.qtdisplay>` component.

The passthrough component's ``transform`` method saves or displays the input frame, but need not do anything else.
The base class takes care of creating the output frame correctly.

Source components
-----------------

Components such as file readers have an output but no inputs.
They use the :py:class:`~pyctools.core.base.Component` base class directly.
In most cases they use an output frame pool and generate a new frame each time a frame object is available from the pool.
See the :py:mod:`ZonePlateGenerator <pyctools.components.zone.zoneplategenerator>` source code for an example.