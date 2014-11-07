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

Getting started
===============

If Pyctools has been installed correctly the :py:mod:`pyctools-editor <pyctools.tools.editor>` command should launch a program similar to that shown below.

.. image:: /images/editor_1.png

The exact appearance will depend on your computer's operating system and user preferences, but the main functional elements should be the same.

Adding components
-----------------

On the left hand side there is a list of Pyctools components and on the right there is a large empty space where components can be placed and connected, called the "graph area".
Click on ``zone`` in the component list to expand it, then drag ``ZonePlateGenerator`` onto the graph area.
A dialog box pops up asking you to give the new component a name, as shown below.

.. image:: /images/editor_2.png

Accept the suggested name by clicking the ``OK`` button.
A zone plate generator component has now been added to the graph area.

.. image:: /images/editor_3.png

You can move the component around by clicking and dragging it.
Clicking on the component selects it and its border is shown dashed.
Selected components can be deleted with the computer's ``delete`` key.

Click on ``qt`` and drag a ``QtDisplay`` component to the graph area.

.. image:: /images/editor_4.png

Connecting components
---------------------

Now click and drag the ZonePlateGenerator's ``output`` connector to the QtDisplay's ``input`` (or *vice versa*).
This connects the two components, as shown below.
(To delete the connection, select the link and press the ``delete`` key.
The easiest way to select the link is to click and drag across it to select an area of the graph that includes the link.)

.. image:: /images/editor_5.png

Component configuration
-----------------------

Double click on the ZonePlateGenerator, or right-click on it and select ``configure`` from the pop-up menu.
This opens the component's configuration dialog, as shown below.
(You should move the dialog so it won't be hidden by the main window.)

.. image:: /images/editor_6.png

Set the following values in the configuration dialog:

* ``kx`` 0.5
* ``kx2`` 1.0
* ``ky`` 0.5
* ``ky2`` 1.0
* ``looping`` repeat
* ``xlen`` 200
* ``ylen`` 200

then click on the ``apply`` button.

.. image:: /images/editor_7.png

Running the graph
-----------------

Clicking on the ``run graph`` button should start the components running.
Another window opens showing the video output from the ZonePlateGenerator.
This is the classic "static circular" zone plate test pattern.

.. image:: /images/editor_8.png

Bring the configuration dialog to the foreground again (by double clicking on the ZonePlateGenerator component) and set the ``kt`` value to 0.1, then click on the ``apply`` button.
Now the zone plate should show some movement.
Hopefully your computer is powerful enough to generate a smoothly moving video.

.. image:: /images/editor_9.png

Being able to update the configuration while the graph is running makes it very easy to experiment with the zone plate generator.
Try setting the ``kt`` value to 0.9 instead of 0.1.

Saving the graph
----------------

Finally, you can save the graph, with all its connections and configuration, to use later.
The ``file`` menu has ``load script`` and ``save script`` actions, with the usual keyboard shortcuts.

Note that you can run your saved script directly, without running :py:mod:`pyctools-editor <pyctools.tools.editor>`.
If you've saved it as ``zone-plate.py`` you can run it with the command ``python zone-plate.py``.