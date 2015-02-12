.. This file is part of pyctools http://github.com/jim-easterbrook/pyctools
   Copyright pyctools contributors
   Released under the GNU GPL3 licence

Contributing to pyctools
========================

You can contribute to pyctools development in two ways.

If you would like to add components related to a particular subject area you might consider publishing a pyctools extension project.
This allows you to keep full control of (and responsibility for) your contribution.
The ``src/examples/simple`` directory is probably a good starting point.

If you want to add to the pyctools core, or fix problems with the existing components, you can do so as follows.

#. Join `GitHub <https://github.com/>`_ - it's free.
#. Fork the pyctools repo - see `Fork a Repo <https://help.github.com/articles/fork-a-repo/>`_ for help.
#. Clone your fork to a computer you can use to develop and test your new feature.
#. Use git to commit changes as you make them and push the changes to your fork of pyctools.
   
   Please add a signed-off-by line to your commits which certify your developer certificate of origin (see below).
   For example, if your name is “John Smith”, and your email address is "jsmith@example.com", just include the following line at the bottom of your commit messages:

       Signed-off-by: John Smith <jsmith@example.com>

   You should be able to do this automatically by using the ``-s`` option on your ``git commit`` commands.
#. Add your name and email to the ``src/contributors.txt`` file.
   Don't forget the ``-s`` option when you commit this change.
#. Test your changes!
#. When everything's working as you expect, submit a `Pull Request <https://help.github.com/articles/using-pull-requests/>`_.

Developer Certificate of Origin
-------------------------------

Including a signed-off-by line in your commits indicates that you certify the following:

.. include:: src/DCO.txt
   :literal:

Clauses (a), (b) and (c) reassure pyctools users that the project will remain open source well in to the future.
Clause (d) reminds you that your contributions will be publicly available, and you do not have the right to withdraw them in future.
