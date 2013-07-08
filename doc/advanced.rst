Advanced Functionality
======================

Adding extra information to ``xpd.xml``
----------------------------------------

The ``<binary_only>`` tag
.........................

If a module in your repository builds to a library (see the
``xcommon`` documentation for details on this). It is possible to
specify that it should only be packaged as a binary.

::

   <binary_only>module_mylib</binary_only>

This means that when a zip file is created only the binary and the
exported source directories of that module are copied into the zip.

The ``<vendor>`` tag
....................

The ``<vendor>`` element is used to specify a company responsible for support,
release and maintenance of a repository. For all repositories developed in the
company this should have a value of ``XMOS``. For a purely open source
community repository this can be omitted.

The ``<maintainer>`` tag
........................

The ``<maintainer>`` elements is used to specify the github username of the
maintainer of the repository or the XMOS email if it is a gitweb repo.

The ``<keyword>`` tag
.....................

Keywords can be added to the ``xpd.xml`` file in ``<keyword>``
elements. 

The ``<scope>`` tag
...................

The ``<scope>`` element gives the scope the repository. It is usually
one of:

  :Prototype:  Proofs of concept with no guarantees of functionality,
               stability etc.

  :Example:    Example code for use in development - these can be
               quite complete but not necessarily productized by a 
               particular vendor.

  :Product:    A repository that is intended to be productized (with
               all the quality, support and validation that entails)
               by a particular vendor.

  :Reference Design:    A repository that provides a complete
                        end-system application to be provided by
                        a vendor to be used with a set of use
                        cases/modifications.

The ``<docdir>`` tag
....................

Several ``docdir`` tags can be added which can contain a
path to a documentation directory relative to the top-level of the
repository. The documents in these directories will be built when a
package is built.

The ``<include_dir>`` and ``<exclude_dir>`` tags
................................................

The xml can contain several ``include_dir`` or several ``exclude_dir`` tags
which specify a list of directories to include (to the exclusion of
all others) or a list of directories to exclude when packaging.


The ``<partnumber>`` and ``<subpartnumber>`` tags
.................................................

These tags relate to part numbers of a repository in a vendor's
document management system. For XMOS repositories this is handled by
the ``--upload`` flag to xpd.

Creating and releasing a custom branch of a release
---------------------------------------------------

Sometimes you may need to create a branch of an existing release
e.g. some custom modifications for a specific project. Say you wish to
modify the ``sc_xtcp`` repository and your changes involve modifying
both that repo and the ``sc_ethernet`` repo. The first thing is to
fork the main repository - either within github or to your local git
server. Next clone these forked repositories into a local sandbox and
checkout the release. Let's say you want to branch of the 1.1.0 release::

        xpd checkout 1.1.0

Now you need to branch the repositories you wish to modify in
git::

        cd sc_xtcp
        git branch mybranch
        git checkout mybranch
        cd ..
        cd sc_ethernet
        git branch mybranch
        git checkout mybranch


After making, committing and pushing your changes. You can now create
your release::

       xpd create_release -v 1.1.0 -b mybranch 

This will create a release called ``1.1.0_mybranch0``. If you make
more modifications, the next release will be called
``1.1.0_mybranch1`` and so on.

