Advanced Functionality
======================

Adding extra release information to ``.xpkg``
---------------------------------------------

The ``<binary_only>`` tag
.........................

If a module in your repository builds to a library (see the
``xcommon`` documentation for details on this). It is possible to
specify that it should only be packaged as a binary.

::

   <binary_only>module_mylib</binary_only>

This means that when a zip file is created only the binary and the
exported source directories of that module are copied into the zip.

The ``<export_git>`` tag
........................

By default, when a zip is made of a particular release, a copy of the
git information for that repo will be packaged. If you wish the
repository to only be packaged without the git history, you can add::

  <export_git>False</export_git>

to the ``.xpkg`` file.

If the git history is not exported then a ``<version>`` and/or
``<githash>`` tag is added to the ``.xpkg`` file in the zip for that
repository showing what version the current snapshot is.

Use cases
---------

Use cases describe the quality of the release. The quality of a
released package is not always an "all or nothing"
property. Generally, validation will have been done for specific
uses. The use cases describe the status of these uses.

There can be several ``<use_case>`` elements within the ``.xpkg``
file. Each one specifies:

   * The type of the use case: *general*, *development* or *invalid*
   * A description of the use case
   * The supported tools versions for that use case
   * The supported XMOS devices for that use case (i.e. the processors)
   * The supported XMOS device hardware for that use case (i.e. the
     boards)
   * A table of supported configurations that constitute the use case

This information is intended to supply a summary of expected use for
people wanting to incorporate a software release into their design. It
is information that could be displayed alongside releases through
various distribution methods.

The ``type`` attribute
......................

.. list_table::
  
  * - ``general``
    - blah
  * - ``development``
    - blah
  * - ``invalid``
    - blah

The ``toolchain`` list
......................

The ``hardware`` list
.....................

The ``devices`` list
....................


Creating and releasing a custom branch of a release
-----------------------------------------------------



Sometimes you may need to create a branch of an existing release
e.g. some custom modifications for a specific project. Say you wish to
modify the ``sc_xtcp`` repository and your changes involve modifying
both that repo and the ``sc_ethernet`` repo. The first thing is to
fork the main repository - either within github or to your local git
server. Next clone these forked repositories into a local sandbox and
checkout the release. Let's say you want to branch of the 1.1.0 release::

        xpkg checkout 1.1.0

Now you need to branch the repositories you wish to modify in
git::

        cd sc_xtcp
        git branch mybranch
        git checkout mybranch
        cd ..
        cd sc_ethernet
        git branch mybranch
        git checkout mybranch


After making, commiting and pushing your changes. You can now create
your release::

       xpkg create_release -v 1.1.0 -b mybranch 

This will create a release called ``1.1.0_mybranch0``. If you make
more modifications, the next release will be called
``1.1.0_mybranch1`` and so on.
      
