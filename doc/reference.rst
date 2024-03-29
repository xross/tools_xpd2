Command Reference
=================

The xpd utility is a command line utility that allows the user to
manipulate dependencies and releases it is called in the following manner.

:: 

  xpd command [options]


The following section describes the possible commands.

Commands
--------

.. option:: init 

   Initialize the ``xpd.xml`` file in the repository.

.. option:: checkout <VERSION>

   Checkout a version of the repository.

   This command will checkout the version request on the repository
   and the compatible versions on all the dependent repositories. 
   
.. option:: update 

   Check and update the repository meta-information.

.. option:: create_release 

   Create a release of the repository. 

   This command will create a new release of the repository. It will
 
     * Update the dependencies in the same way as the ``update_deps`` option. 
     * Update the repository's meta-information with the new release 
       based on the current state of the repository and its
       dependents.
     * Commit the new meta-information to the repository.

   The command will create a new release with a release number that is
   either a major, minor or point increment to the latest full
   release. 

.. option:: publish

   Publish the current version to cognidox.

.. option:: build_results [MODULE]

   Create the auto-generated source code for all modules (or the one specified).
   This command generates the resource usage output for each configuration that
   a module supports. The resource usage output can be found in the ``xpd`` log
   file (``run_xpd.log`` by default).

.. option:: list

   List the release versions of this repository.

.. option:: make_zip

   Make a zip file of the specified version.

.. option:: tag <VERSION>

   Tag the repository with a version.

   This option tags the repository with a particular version. It also
   marks the version as external in the meta-information.
   
.. option:: add_dep <REPO_NAME>

   Add a dependency.

   This commands adds a new known dependency to the repository.

.. option:: remove_dep <REPO_NAME>

   Remove a dependency.

   This commands removes a known dependency to the repository.

.. option:: show_deps

   Show a tree view of the dependencies for the repository.

.. option:: get_deps [VERSION]

   Clone all the dependent repositories that are missing. If a version
   is specified then the dependencies for that version will be cloned.

   Note that if the dependencies fail to clone with the following error
   message:

   ``Permission denied (publickey).``
   
   Then it is necessary to set up your ssh keys. See 
   ``https://help.github.com/articles/generating-ssh-keys``


.. option:: check_deps

   Checks the known dependencies of the repository
   against all the ones that are needed due to the USED_MODULES 
   variables in the various application Makefiles within the repository.

.. option:: update_deps

   Update all dependencies to their current version. Removes unused
   dependencies.

.. option:: check_info

   Check repository meta-information. 

   This command checks the repository meta-information for validity
   and if any information is missing will prompt the user to enter it.
   
.. option:: check_infr

   Check repository infrastructure (Makefiles, eclipse project files).

.. option:: list

   List releases.

   This commands lists the releases of the repo.

.. option:: status

   Show status information.

   This command displays information about the current repository version and
   its dependencies.

.. option:: create_app [NAME]

   Create the skeleton for a new application with the specified name.

.. option:: create_module [NAME]

   Create the skeleton for a new module with the specified name.

.. option:: git command

   Iterate the given git command over the repo and all its dependencies.

.. option:: validate_swblock <BLOCK_NAME>

   Validate the meta-data of the specified software block.

.. option:: --upload

   If specified with the ``make_zip`` of ``create_release`` command
   then ``xpd`` will upload the release to cognidox.
