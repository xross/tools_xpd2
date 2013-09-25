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
