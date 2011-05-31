Command Reference
=================

The xpkg utility is a command line utility that allows the user to
manipulate dependencies and releases it is called in the following manner.

:: 

  xpkg command [options]


The following section describes the possible commands.

Commands
--------

.. option:: init 

   Initialize the ``xpkg.xml`` file in the repository.

   This command will initialize the meta-data file in the repository. 

.. option:: checkout version

   Checkout a version of the repository.

   This command will checkout the version request on the repository
   and the compatible versions on all the dependent repositories. 
   
.. option:: create_release 

   Create a release of the repository. 

   This command will create a new release of the repository. It will
 
     * Check the dependencies in the same way as the
       :option:`check_dep` option. 
     * Update the repositories meta-information with the new release 
       based on the current state of the repository and its
       dependents.
     * Commit the new meta-information to the repository.

   The command will create a new release with a release number that is
   either a major, minor or point increment to the latest full
   release. 

.. option:: upgrade_rc version

   Upgrade a release candidate into a release.

   The command will record a release version to be the same as the
   latest release candidate for that version. 

.. option:: list

   List the release versions of this repository.

.. option:: make_zip version

   Make a zip file of the specified version.

.. option:: tag version

   Tag the repository with a version.

   This option tags the repository with a particualr version. It also
   marks the version as external in the meta-information.
   
.. option:: add_dep repo_name

   Add a dependency.

   This commands adds a new known dependency to the repository.

.. option:: remove_dep repo_name

   Remove a dependency.

   This commands removes a known dependency to the repository.

.. option:: check_dep

   Check dependencies.
 
   This commands checks the known dependencies of the repository
   against all the ones that are needed due to the USED_MODULES 
   variables in the various application Makefiles within the repository.

.. option:: check_info

   Check repository meta-information. 

   This command checks the repository meta-information for validity
   and if any information is missing will prompt the user to enter it.
   
.. option:: gen_readme

   Generate a readme.

   This command will generate a readme and output it to standard
   output. This can be used for the README.rst file in the repository.

.. option:: list

   List releases.

   This commands lists the releases of the repo.

.. option:: show [version]

   Show version information.

   This command display the version information about a particuar version.

.. option:: git command

   Iterate the given git command over the repo and all its dependencies.



