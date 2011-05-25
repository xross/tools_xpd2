Tutorial
========

For this tutorial, we will take the example of the sc_xtcp
repository. Not that the actual sc_xtcp repository on xcore may not
have the same versions or githashes as in the tutorial.

The basics
----------

The sc_xtcp repository depends on other repositories for its code. In
particular it uses modules from the sc_ethernet repository and its
build structure is taken from the xcommon repository. So a local
sandbox will look something like this::

   sc_xtcp/
   sc_ethernet/
   xcommon/

You local sandbox or working directory will contain certain versions
of each of these repositories and each will be under version control
using git.

The ``show`` command will give you information about the current state
of a repository including its meta-information and dependencies::


   $ cd sc_xtcp
   $ xpkg show
   INFO:
    
                 Name: sc_xtcp
              Version: da8fc727e3d3543bdbe56bdd15bfde4b9c7acb52
                 Icon: icon/sc_xtcp.png
             Location: ssh://git@github.com/davelxmos/sc_xtcp
        Documentation: http://xcore.github.com/sc_xtcp
          Description: A TCP/IP stack component. This component is a
                       port of the uIP stack. 
                       It requires sc_ethernet to function.
    
   DEPENDENCIES:
    
   Actual:
                xcommon: e1a96de831569a0083c79a46f6de68801cbf6e31 
            sc_ethernet: bde2c75ff0364ff9973ead0c5d18e537cedd4941
    
   Expected:
                xcommon: 1.0.0
            sc_ethernet: 2.0.0

The tool has shown us several things. Firstly, some meta information
is shown about the repository and along with the current version the
repo is at. There is also some dependency information shown. The
actual section shows what versions the local working directory copies
of the repositories are at. The expected section shows what the meta
information has recorded as being working dependencies. These are the
versions of the dependencies that were set when the last release was
created (or when the dependencies were last updated and commited back
to the repository).

.. note::

   All the information that the tool uses is stored in a file called
   ``.xpkg`` which is at the top-level of the repository.


In this example, we can see that all three repositories are at
versions in git that do not correspond to a particular release (hence
the versions are given as git hashes). This is quite common if you are
working at the develpment head of the repositories. 

The ``list`` command can show you what releases have been created in
the past for this repository::
   $ xpkg list
   2.1.0alpha0
   2.0.0
   2.0.0rc0
   2.0.0beta1
   2.0.0beta0
   ...

The ``checkout`` command can move to a specific release. It works like
the git checkout command but also checks out the relevant
dependencies::

   $ xpkg checkout 2.0.0

Once we have checked out this version, it is possible to look at the
information for this version:: 

   $ xpkg show
   INFO:
    
                 Name: sc_xtcp
              Version: 2.0.0
                 Icon: icon/sc_xtcp.png
             Location: ssh://git@github.com/davelxmos/sc_xtcp
        Documentation: http://xcore.github.com/sc_xtcp
          Description: A TCP/IP stack component. This component is a
                       port of the uIP stack. 
                       It requires sc_ethernet to function.
    
   DEPENDENCIES:
    
   Actual:
                xcommon: 1.0.0 
            sc_ethernet: 2.0.0
    
   Expected:
                xcommon: 1.0.0
            sc_ethernet: 2.0.0


Here we can see that the actual versions of our local repositories
have changed. We can get back to the master branch using xpkg checkout again::

   $ xpkg checkout master

If checkout gets an argument which is not a version number it tries to
change all repositories to the specified ref using git.

Running git commands
--------------------

It is possible to iterate git commands over all dependent repositories
using the ``xpkg git`` command. So, the following will call ``git
status`` on the main repository and all its dependents::

   $ xpkg git status

Updating dependencies
---------------------

As we have seen, ``xpkg`` keeps track of the repositories your
repository depends upon. To maintain this list you can use the
``show_dep``, ``check_dep``, ``add_dep`` and ``remove_dep`` commands. 

The main command to use is the ``check_dep`` command. This checks the
current dependencies and offers to update meta-information if new or
changed dependencies are found e.g.::
  
 $ xpkg check_dep
 Add xcommon to dependencies (Y/n)?y
 Added
 Add sc_ethernet to dependencies (Y/n)?y
 Added

Checking metainformation
------------------------

You can also check the current state of the meta-information in the
repository with the ``show`` and ``check_info`` commands. The
``check_info`` commands checks what meta-information is defines and
asks you to update it with anything that is missing.

Creating releases
-----------------

Creating a release is a matter of:

  #. Check that all the dependency information and meta information is
     as you want it for the release.
  #. Run ``xpkg create_release`` 

The ``create_release`` command will prompt you for a version number
and type (e.g. alpha, beta etc). It will check dependencies, update
the .xpkg file with the release information and make a commit to the
repository which represents the release. It will then ask if you want
to make a zip of the release. The zip will contain the repository and
all its dependencies so is self contained for anyone who wishes to use it.

Tagging
-------

By default, a release is not tagged in the git repository. The idea is
that only releases that may be of external interest (public betas,
generally available releases) are tagged.

To tag a particular release you can use ``xpkg`` e.g.::

   xpkg tag 2.0.0

This will tag the git repository at the correct githash with the tag ``v2.0.0``.
