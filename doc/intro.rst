Introduction
============

``xpd`` is a python script that performs package management for XMOS
and xcore source code repositories. The tool:

   * Tracks dependencies of the repository
   * Manages repository meta-information
   * Manages releases (and their dependencies)

Using this tool is highly recommended for release management of your
repository since it is maintained by XMOS and is designed to be compatible with
future features in the both the XMOS development tools and the xcore
open source repositories.

*Note:* it is necessary to have the XMOS command-line tools in the path when
running ``xpd``. Otherwise not all ``xpd`` commands will work.

Log Files
---------

``xpd`` displays information to the console as it runs. However, this information
is limited to the key messages that the user needs to know about. While it runs
``xpd`` also emits a much more verbose set of messages to a log file (``run_xpd.log``
by default). This log file contains details of all sub-commands run by ``xpd``
and gives the output of those processes.
