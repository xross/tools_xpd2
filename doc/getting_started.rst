Getting Started
===============

Before installing xpd you need to have python installed on your system.

The xpd github repository can be found here:

  http://github.com/xcore/tool_xpd

To install, first clone the repository::

  git clone http://github.com/xcore/tool_xpd

and then run the ``setup.py`` script::

  cd tool_xpd
  python setup.py install

This should put the script ``xpd`` into your executable path. You
will probably need superuser/administrator priveledges to do this.

Creating an ``xpd.xml`` file
-----------------------------

To get going in a new repository, just change into the repository
directory and run::

  xpd init

You can now add the ``xpd.xml`` file to your git repo::

  git add xpd.xml
  git commit -m "Added xpd.xml"  
