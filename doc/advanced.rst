Advanced Functionality
======================

Adding extra information to ``xpkg.xml``
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

The ``<export_git>`` tag
........................

By default, when a zip is made of a particular release, a copy of the
git information for that repo will be packaged. If you wish the
repository to only be packaged without the git history, you can add::

  <export_git>False</export_git>

to the ``xpkg.xml`` file.

If the git history is not exported then a ``<version>`` and/or
``<githash>`` tag is added to the ``xpkg.xml`` file in the zip for that
repository showing what version the current snapshot is.

The ``<vendor>`` and ``maintainer`` tag
.......................................

The ``<vendor>`` element is used to specify a company responsible for support,
release and maintenaince of a repository. For a purely open source
community repository this can be omitted.

The ``<maintainer>`` elements is used to specify the github username of the
maintainer of the repository.

The ``<keyword>`` tag
.....................

Keywords can be added to the ``xpkg.xml`` file in ``<keyword>``
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
               by a particualr vendor.

  :Reference Design:    A repository that provides a complete
                        end-system application to be provided by
                        a vendor to be used with a set of use
                        cases/modifications.

Use cases
---------

When a release is made be a vendor for a particular distribution
channel you want to say something about the quality, support and
expected use of the release. Use cases give information on this though
for a definite answer contactor the vendor. 

If your project is a general open source "as-is" project or in early
development you do not need to worry about use cases.

Use cases describe the quality of the release. The quality of a
released package is not always an "all or nothing"
property. Generally, validation will have been done for specific
uses. The use cases describe the status of these uses.

There can be several ``<use_case>`` elements within the ``xpkg.xml``
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

Each use case will have a type which determines under what situation
the it is expected to be used. The type can be one of ``general``,
``development`` or ``invalid``

.. list-table::
  :header-rows: 1
  
  * - Use Case Type
    - Description
  * - ``general``
    - This use case is endorsed by the vendor to work
      properly. Typically, this will have involved a
      substantial amount of testing/validation and quality 
      assurance. This case is particular relevant to reference 
      designs
  * - ``development``
    - This use case is expected to function properly by the vendor and
      is suitable for building into a design. The vendor will have
      completed development and testing of the components involved but 
      obviously it is up to the user to validate the integration of
      this use case into their design.
  * - ``invalid``
    - This use case is known not to work.

The ``toolchain`` list
......................

The ``<toolchain>`` element will contain a list of ``<tools>``
elements detailing all the development tools versions that the use
case works with, for example::

        <toolchain>
            <tools>11.2.0</tools>
            <tools>11.2.1</tools>
        </toolchain>

The ``hardware`` list
.....................

The ``<devices>`` element will contain a list of ``<board>``
and ``<schematic>`` elements detailing all the boards the the use case
works with, for example::

            <board portmap = "app_ipod_dock_lite/src/ipod_dock_2v0.h">XR-IPOD-DOCK-2V0</board>
            <schematic portmap = "app_ipod_dock_lite/src/ipod_dock_2v0.h">Legacy 1v3 Schematic</schematic>

The ``portmap`` attribute shows the header file or XN file that
details the portmap of the board and its relation to the software.

The ``devices`` list
....................

The ``<devices>`` element will contain a list of ``<device>``
elements detailing all the devices (i.e. XMOS chips) that the
case works with, for example::

        <devices>
            <device>XS1-L01A-LQ64-I5</device>
        </devices>

The configuration tables
........................

The configuration tables within a use case is just a list of html
tables (with not style) detailing required or possible configurations
that define the use case, for example::

   <table>
      <caption>Required build option settings</caption>
      <tr>
        <th>Option<th>
        <th>Value</th>
      </tr>
      <tr>
        <td>SAMPLE_FREQUENCY</td>
        <td>48000 or 96000</td>
      <tr>
      <tr>
        <td>CODEC_AS_I2S_MASTER</td>
        <td>1</td>
      <tr>

Ideally, the table should have one vertical or horizontal header row.

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
      
