Tutorial
========

For this tutorial, we will take the example of the ``sc_xtcp`` repository.
Clone it using git::

    git clone git://github.com/xcore/sc_xtcp
    cd sc_xtcp

Dependencies
------------

The ``sc_xtcp`` repository depends on other repositories for its code. In
particular it uses modules from the ``sc_ethernet`` repository. In order to
get the dependent repositories use::

    xpd getdeps

This will clone repositories that are required by this repository leaving a
sandbox that looks something like this::

   sc_xtcp/
   sc_ethernet/
   sc_otp/

You local sandbox or working directory will contain certain versions
of each of these repositories and each will be under version control
using git.

The basics
----------

The ``status`` command will give you information about the current state
of a repository including its meta-information and dependencies::

   $ xpd status
   INFO:

              Name: sc_xtcp
           Version: c6f4dfadfffd9ad49e6870d9c3447f7f0a634637
          Location: ssh://git@github.com/davelxmos/sc_xtcp
       Description: Implementation of uIP TCP/IP stack for XMOS devices. Runs in a single thread.
     Documentation: doc/xtcp_guide
                    doc/slicekit_quickstart
    
    SOFTWARE BLOCKS
    
    Apps:
    
    Simple HTTP Demo
           Name: Simple HTTP Demo
          Scope: Example
    Description: A demo of the TCP/IP stack that provides a simple webserver
       Keywords: ethernet,tcp/ip,webserver,http
      Published: True
    
    
    Modules:
    
    Ethernet/TCP Module
           Name: Ethernet/TCP Module
          Scope: General Use
    Description: An ethernet stack with TCP/IP
       Keywords: ethernet,TCP/IP,mac,mii,IP,UDP,ICMP,UDP
      Published: True


   DEPENDENCIES:
    
   Actual:
                xcommon: e1a96de831569a0083c79a46f6de68801cbf6e31 
            sc_ethernet: bde2c75ff0364ff9973ead0c5d18e537cedd4941
    
   Expected:
                xcommon: 1.0.0
            sc_ethernet: 2.0.0

The tool has shown us several things. Firstly, some meta information
is shown about the repository and along with the current version the
repo is at.

There is information about the software blocks within this repository.
These are divided into applications and modules as classified within
the ``xpd.xml`` file.

There is also some dependency information shown. The ``Actual``
section shows what versions the local working directory copies
of the repositories are at. The ``Expected`` section shows what the meta
information has recorded as being working dependencies. These are the
versions of the dependencies that were set when the last release was
created (or when the dependencies were last updated and committed back
to the repository).

.. note::

   All the information that the tool uses is stored in a file called
   ``xpd.xml`` which is at the top-level of the repository.

In this example, we can see that all three repositories are at
versions in git that do not correspond to a particular release (hence
the versions are given as git hashes). This is quite common if you are
working at the development head of the repositories. 

Release versions
----------------

The ``list`` command can show you what releases have been created in
the past for this repository::

   $ xpd list
   3.1.2rc1
   3.1.2rc0
   3.1.1rc3
   3.1.1rc2
   ...

The ``checkout`` command can move to a specific release. It works like
the git checkout command but also checks out the relevant
dependencies::

   $ xpd checkout 3.1.1rc2

Once we have checked out this version, it is possible to look at the
information for this version:: 

   $ xpd status
   INFO:
   
                 Name: sc_xtcp
              Version: 3.1.1rc2
             Location: ssh://git@github.com/davelxmos/sc_xtcp
          Description: Implementation of uIP TCP/IP stack for XMOS devices. Runs in a single thread.
        Documentation: doc/xtcp_guide
                       doc/slicekit_quickstart

   ...
   
   DEPENDENCIES:
   
   Actual:
            sc_ethernet: 2.2.1rc1
                 sc_otp: 1.0.0rc0
   
   Expected:
            sc_ethernet: 2.2.1rc1
                 sc_otp: 1.0.0rc0

Here we can see that the actual versions of our local repositories
have changed. We can get back to the head of the master branch using
xpd checkout again::

   $ xpd checkout master

If checkout gets an argument which is not a version number it tries to
change all repositories to the specified ref using git.

Running git commands
--------------------

It is possible to iterate git commands over all dependent repositories
using the ``xpd git`` command. So, the following will call ``git status``
on the main repository and all its dependents::

   $ xpd git status

Updating dependencies
---------------------

As we have seen, ``xpd`` keeps track of the repositories your
repository depends upon. To maintain this list you can use the
``show_dep``, ``check_dep``, ``add_dep`` and ``remove_dep`` commands. 

The main command to use is the ``check_dep`` command. This checks the
current dependencies and automatically updates the dependencies in
xpd.xml::
  
   $ xpd check_dep
   Saving xpd.xml

Checking repository information
-------------------------------

You can check the current state of the repository information
with the ``status`` and ``check_info`` commands. The
``check_info`` commands checks what repository information is defined and
asks you to update it with anything that is missing.

Creating releases
-----------------

Creating releases involves the following steps:

  #. Create alphas and betas for testing (optional, during development
     phase)
  #. Create release candidates until one is ready for full release

Creating an alpha, beta or release candidate is a matter of:
 
  #. Check that all the dependency information and meta information is
     as you want it for the release.
  #. Add release notes and changelog entries to ``CHANGELOG.rst``
  #. Run ``xpd create_release`` 

The ``create_release`` command will prompt you for the release type
and version number. It will check dependencies, update
the ``xpd.xml`` file with the release information and make a commit to the
repository which represents the release. 

Tagging
-------

By default, a release is not tagged in the git repository. The idea is
that only releases that may be of external interest (public betas,
generally available releases) are tagged.

To tag a particular release you can use ``xpd`` e.g.::

   xpd tag 2.0.0

This will tag the git repository at the correct githash with the tag ``v2.0.0``.
