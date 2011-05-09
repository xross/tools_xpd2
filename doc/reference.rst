Reference
=========

The xpkg utility is a command line utility that allows the user to
manipulate dependencies and releases it is called in the following manner.

:: 

  xpkg command [options]


The following section describes the possible commands.

Commands
--------

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

.. option:: tag version

   Tag the repository with a version.

   This option tags the repository with a particualr version. It also
   marks the version as external in the meta-information.
   
.. option:: add_dep path_to_repo

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

.. option:: list

   List releases.

   This commands lists the releases of the repo.

.. option:: show [version]

   Show version information.

   This command display the version information about a particuar version.

.. option:: git command

   Iterate the given git command over the repo and all its dependencies.

.. option:: remove version

   Remove a version

   This removes a version from the repository meta-information.


