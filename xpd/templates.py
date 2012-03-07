toplevel_makefile = '''
# This variable should contain a space separated list of all
# the directories containing buildable applications (usually
# prefixed with the app_ prefix)
#
# If the variable is set to "all" then all directories that start with app_
# are built.
BUILD_SUBDIRS = all

XMOS_MAKE_PATH ?= ..
include $(XMOS_MAKE_PATH)/xcommon/module_xcommon/build/Makefile.toplevel
'''

app_makefile = """
# The TARGET variable determines what target system the application is
# compiled for. It either refers to an XN file in the source directories
# or a valid argument for the --target option when compiling
TARGET =

# The APP_NAME variable determines the name of the final .xe file. It should
# not include the .xe postfix. If left blank the name will default to
# the project name
APP_NAME =

# The USED_MODULES variable lists other module used by the application.
USED_MODULES =

# The flags passed to xcc when building the application
# You can also set the following to override flags for a particular language:
# XCC_XC_FLAGS, XCC_C_FLAGS, XCC_ASM_FLAGS, XCC_CPP_FLAGS
# If the variable XCC_MAP_FLAGS is set it overrides the flags passed to
# xcc for the final link (mapping) stage.
XCC_FLAGS_Debug = -g -O0 -Wcodes -Xmapper -Wcodes
XCC_FLAGS_Release = -g -O3 -Wcodes -Xmapper -Wcodes

# The VERBOSE variable, if set to 1, enables verbose output from the make system.
VERBOSE = 0

#=============================================================================
# The following part of the Makefile includes the common build infrastructure
# for compiling XMOS applications. You should not need to edit below here.

XMOS_MAKE_PATH ?= ../..
ifneq ($(wildcard $(XMOS_MAKE_PATH)/xcommon/module_xcommon/build/Makefile.common),)
include $(XMOS_MAKE_PATH)/xcommon/module_xcommon/build/Makefile.common
else
include ../module_xcommon/build/Makefile.common
endif
"""

module_build_info = '''
# You can set flags specifically for your module by using the MODULE_XCC_FLAGS
# variable. So the following
#
#   MODULE_XCC_FLAGS = $(XCC_FLAGS) -O3
#
# specifies that everything in the modules should have the application
# build flags with -O3 appended (so the files will build at
# optimization level -O3).
#
# You can also set MODULE_XCC_C_FLAGS, MODULE_XCC_XC_FLAGS etc..
'''


cproject = '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<?fileVersion 4.0.0?>
<cproject storage_type_id="org.eclipse.cdt.core.XmlProjectDescriptionStorage">
    <storageModule moduleId="org.eclipse.cdt.core.settings">
              %CONFIGURATIONS%
    </storageModule>
    <storageModule moduleId="cdtBuildSystem" version="4.0.0">
        <project id="%PROJECT%.null.1239749732" name="%PROJECT%" />
    </storageModule>
</cproject>
'''

cproject_configuration = '''
        <cconfiguration id="com.xmos.cdt.toolchain.%CONFIG_ID%">
            <storageModule buildSystemId="org.eclipse.cdt.managedbuilder.core.configurationDataProvider" id="com.xmos.cdt.toolchain.%CONFIG_ID%" moduleId="org.eclipse.cdt.core.settings" name="%CONFIG%">
                <externalSettings />
                <extensions>
                    <extension id="com.xmos.cdt.core.XEBinaryParser" point="org.eclipse.cdt.core.BinaryParser" />
                    <extension id="com.xmos.cdt.core.XdeErrorParser" point="org.eclipse.cdt.core.ErrorParser" />
                    <extension id="org.eclipse.cdt.core.GCCErrorParser" point="org.eclipse.cdt.core.ErrorParser" />
                </extensions>
            </storageModule>
            <storageModule moduleId="cdtBuildSystem" version="4.0.0">
                <configuration buildProperties="" description="" id="com.xmos.cdt.toolchain.%CONFIG_ID%" name="%CONFIG%" parent="org.eclipse.cdt.build.core.emptycfg">
                    <folderInfo id="com.xmos.cdt.toolchain.%CONFIG_ID%.1127281840" name="/" resourcePath="">
                        <toolChain id="com.xmos.cdt.toolchain.1842437102" name="com.xmos.cdt.toolchain" superClass="com.xmos.cdt.toolchain">
                            <targetPlatform archList="all" binaryParser="com.xmos.cdt.core.XEBinaryParser" id="com.xmos.cdt.core.platform.942407365" isAbstract="false" osList="linux,win32,macosx" superClass="com.xmos.cdt.core.platform" />
                            <builder arguments="%CONFIG_ARGS%" id="com.xmos.cdt.builder.base.2141163380" keepEnvironmentInBuildfile="false" managedBuildOn="false" superClass="com.xmos.cdt.builder.base" />
                            <tool id="com.xmos.cdt.xc.compiler.73393562" name="com.xmos.cdt.xc.compiler" superClass="com.xmos.cdt.xc.compiler">
                                <option id="com.xmos.c.compiler.option.include.paths.569332846" name="com.xmos.c.compiler.option.include.paths" superClass="com.xmos.c.compiler.option.include.paths" valueType="includePath">
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_TOOL_PATH}/target/include&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_TOOL_PATH}/target/include/gcc&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_TOOL_PATH}/target/include/c++/4.2.1&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_TOOL_PATH}/target/include/c++/4.2.1/xcore-xmos-elf&quot;' />
                                    %INCLUDES%
                                </option>
                                <inputType id="com.xmos.cdt.xc.compiler.input.1177118008" name="XC Sources" superClass="com.xmos.cdt.xc.compiler.input" />
                                <option id="gnu.c.compiler.option.include.paths.11111" valueType="includePath" superClass="gnu.c.compiler.option.include.paths">
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_TOOL_PATH}/target/include&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_TOOL_PATH}/target/include/c++/4.2.1&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_TOOL_PATH}/target/include/c++/4.2.1/xcore-xmos-elf&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_TOOL_PATH}/target/include/gcc&quot;' />
                                    %INCLUDES%
                                </option>
                            </tool>
                            <tool id="com.xmos.cdt.xc.compiler.base.11111" name="com.xmos.cdt.xc.compiler.base" superClass="com.xmos.cdt.xc.compiler.base">
                                <option id="gnu.c.compiler.option.include.paths.11111" valueType="includePath" superClass="gnu.c.compiler.option.include.paths">
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1/xcore-xmos-elf&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/gcc&quot;' />
                                    %INCLUDES%
                                </option>
                                <option id="com.xmos.c.compiler.option.include.paths.11111" valueType="includePath" superClass="com.xmos.c.compiler.option.include.paths">
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1/xcore-xmos-elf&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/gcc&quot;' />
                                    %INCLUDES%
                                </option>
                            </tool>
                            <tool id="com.xmos.cdt.c.compiler.base.11111" name="com.xmos.cdt.c.compiler.base" superClass="com.xmos.cdt.c.compiler.base">
                                <option id="gnu.c.compiler.option.include.paths.11111" valueType="includePath" superClass="gnu.c.compiler.option.include.paths">
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1/xcore-xmos-elf&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/gcc&quot;' />
                                    %INCLUDES%
                                </option>
                                <option id="com.xmos.c.compiler.option.include.paths.11111" valueType="includePath" superClass="com.xmos.c.compiler.option.include.paths">
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1/xcore-xmos-elf&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/gcc&quot;' />
                                    %INCLUDES%
                                </option>
                            </tool>
                            <tool id="com.xmos.cdt.cpp.compiler.base.11111" name="com.xmos.cdt.cpp.compiler.base" superClass="com.xmos.cdt.cpp.compiler.base">
                                <option id="gnu.c.compiler.option.include.paths.11111" valueType="includePath" superClass="gnu.c.compiler.option.include.paths">
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1/xcore-xmos-elf&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/gcc&quot;' />
                                    %INCLUDES%
                                </option>
                                <option id="com.xmos.c.compiler.option.include.paths.11111" valueType="includePath" superClass="com.xmos.c.compiler.option.include.paths">
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1/xcore-xmos-elf&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/gcc&quot;' />
                                    %INCLUDES%
                                </option>
                            </tool>
                            <tool id="com.xmos.cdt.core.assembler.base.11111" name="com.xmos.cdt.core.assembler.base" superClass="com.xmos.cdt.core.assembler.base">
                                <option id="gnu.c.compiler.option.include.paths.11111" valueType="includePath" superClass="gnu.c.compiler.option.include.paths">
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1/xcore-xmos-elf&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/gcc&quot;' />
                                    %INCLUDES%
                                </option>
                                <option id="com.xmos.c.compiler.option.include.paths.11111" valueType="includePath" superClass="com.xmos.c.compiler.option.include.paths">
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1/xcore-xmos-elf&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/gcc&quot;' />
                                    %INCLUDES%
                                </option>
                            </tool>
                        </toolChain>
                    </folderInfo>
                </configuration>
            </storageModule>
            <storageModule moduleId="scannerConfiguration">
                <autodiscovery enabled="true" problemReportingEnabled="true" selectedProfileId="" />
                <profile id="org.eclipse.cdt.make.core.GCCStandardMakePerProjectProfile">
                    <buildOutputProvider>
                        <openAction enabled="true" filePath="" />
                        <parser enabled="true" />
                    </buildOutputProvider>
                    <scannerInfoProvider id="specsFile">
                        <runAction arguments="-E -P -v -dD ${plugin_state_location}/${specs_file}" command="gcc" useDefault="true" />
                        <parser enabled="true" />
                    </scannerInfoProvider>
                </profile>
                <profile id="org.eclipse.cdt.make.core.GCCStandardMakePerFileProfile">
                    <buildOutputProvider>
                        <openAction enabled="true" filePath="" />
                        <parser enabled="true" />
                    </buildOutputProvider>
                    <scannerInfoProvider id="makefileGenerator">
                        <runAction arguments="-E -P -v -dD" command="" useDefault="true" />
                        <parser enabled="true" />
                    </scannerInfoProvider>
                </profile>
                <profile id="org.eclipse.cdt.managedbuilder.core.GCCManagedMakePerProjectProfile">
                    <buildOutputProvider>
                        <openAction enabled="true" filePath="" />
                        <parser enabled="true" />
                    </buildOutputProvider>
                    <scannerInfoProvider id="specsFile">
                        <runAction arguments="-E -P -v -dD ${plugin_state_location}/${specs_file}" command="gcc" useDefault="true" />
                        <parser enabled="true" />
                    </scannerInfoProvider>
                </profile>
                <profile id="org.eclipse.cdt.managedbuilder.core.GCCManagedMakePerProjectProfileCPP">
                    <buildOutputProvider>
                        <openAction enabled="true" filePath="" />
                        <parser enabled="true" />
                    </buildOutputProvider>
                    <scannerInfoProvider id="specsFile">
                        <runAction arguments="-E -P -v -dD ${plugin_state_location}/specs.cpp" command="g++" useDefault="true" />
                        <parser enabled="true" />
                    </scannerInfoProvider>
                </profile>
                <profile id="org.eclipse.cdt.managedbuilder.core.GCCManagedMakePerProjectProfileC">
                    <buildOutputProvider>
                        <openAction enabled="true" filePath="" />
                        <parser enabled="true" />
                    </buildOutputProvider>
                    <scannerInfoProvider id="specsFile">
                        <runAction arguments="-E -P -v -dD ${plugin_state_location}/specs.c" command="gcc" useDefault="true" />
                        <parser enabled="true" />
                    </scannerInfoProvider>
                </profile>
                <profile id="org.eclipse.cdt.managedbuilder.core.GCCWinManagedMakePerProjectProfile">
                    <buildOutputProvider>
                        <openAction enabled="true" filePath="" />
                        <parser enabled="true" />
                    </buildOutputProvider>
                    <scannerInfoProvider id="specsFile">
                        <runAction arguments='-c &apos;gcc -E -P -v -dD &quot;${plugin_state_location}/${specs_file}&quot;&apos;' command="sh" useDefault="true" />
                        <parser enabled="true" />
                    </scannerInfoProvider>
                </profile>
                <profile id="org.eclipse.cdt.managedbuilder.core.GCCWinManagedMakePerProjectProfileCPP">
                    <buildOutputProvider>
                        <openAction enabled="true" filePath="" />
                        <parser enabled="true" />
                    </buildOutputProvider>
                    <scannerInfoProvider id="specsFile">
                        <runAction arguments='-c &apos;g++ -E -P -v -dD &quot;${plugin_state_location}/specs.cpp&quot;&apos;' command="sh" useDefault="true" />
                        <parser enabled="true" />
                    </scannerInfoProvider>
                </profile>
                <profile id="org.eclipse.cdt.managedbuilder.core.GCCWinManagedMakePerProjectProfileC">
                    <buildOutputProvider>
                        <openAction enabled="true" filePath="" />
                        <parser enabled="true" />
                    </buildOutputProvider>
                    <scannerInfoProvider id="specsFile">
                        <runAction arguments='-c &apos;gcc -E -P -v -dD &quot;${plugin_state_location}/specs.c&quot;&apos;' command="sh" useDefault="true" />
                        <parser enabled="true" />
                    </scannerInfoProvider>
                </profile>
            </storageModule>
            <storageModule moduleId="org.eclipse.cdt.core.externalSettings" />
            <storageModule moduleId="org.eclipse.cdt.core.language.mapping" />
            <storageModule moduleId="org.eclipse.cdt.internal.ui.text.commentOwnerProjectMappings" />
        </cconfiguration>
'''

dotproject = '''
<?xml version="1.0" encoding="UTF-8"?>
<projectDescription>
	<name>%PROJECT%</name>
	<comment></comment>
	<projects>
	</projects>
	<buildSpec>
		<buildCommand>
			<name>com.xmos.cdt.core.SrcCheckerBuilder</name>
			<arguments>
			</arguments>
		</buildCommand>
		<buildCommand>
			<name>org.eclipse.cdt.managedbuilder.core.genmakebuilder</name>
			<triggers>clean,full,incremental,</triggers>
			<arguments>
				<dictionary>
					<key>?name?</key>
					<value></value>
				</dictionary>
				<dictionary>
					<key>org.eclipse.cdt.make.core.append_environment</key>
					<value>true</value>
				</dictionary>
				<dictionary>
					<key>org.eclipse.cdt.make.core.buildArguments</key>
					<value>CONFIG=Debug</value>
				</dictionary>
				<dictionary>
					<key>org.eclipse.cdt.make.core.buildCommand</key>
					<value>xmake</value>
				</dictionary>
				<dictionary>
					<key>org.eclipse.cdt.make.core.cleanBuildTarget</key>
					<value>clean</value>
				</dictionary>
				<dictionary>
					<key>org.eclipse.cdt.make.core.contents</key>
					<value>org.eclipse.cdt.make.core.activeConfigSettings</value>
				</dictionary>
				<dictionary>
					<key>org.eclipse.cdt.make.core.enableAutoBuild</key>
					<value>false</value>
				</dictionary>
				<dictionary>
					<key>org.eclipse.cdt.make.core.enableCleanBuild</key>
					<value>true</value>
				</dictionary>
				<dictionary>
					<key>org.eclipse.cdt.make.core.enableFullBuild</key>
					<value>true</value>
				</dictionary>
				<dictionary>
					<key>org.eclipse.cdt.make.core.stopOnError</key>
					<value>true</value>
				</dictionary>
				<dictionary>
					<key>org.eclipse.cdt.make.core.useDefaultBuildCmd</key>
					<value>false</value>
				</dictionary>
			</arguments>
		</buildCommand>
		<buildCommand>
			<name>org.eclipse.cdt.managedbuilder.core.ScannerConfigBuilder</name>
			<triggers>full,incremental,</triggers>
			<arguments>
			</arguments>
		</buildCommand>
	</buildSpec>
	<natures>
		<nature>org.eclipse.cdt.core.cnature</nature>
		<nature>org.eclipse.cdt.managedbuilder.core.managedBuildNature</nature>
		<nature>org.eclipse.cdt.managedbuilder.core.ScannerConfigNature</nature>
		<nature>com.xmos.cdt.core.XdeProjectNature</nature>
	</natures>
</projectDescription>
'''

xcore_license = '''
Software License Agreement

Copyright (c) 2011, %(holder)s, All rights reserved.

Additional copyright holders (each contributor holds copyright
over contribution as described in the git commit logs for the repository):

        <list additional contributors and github usernames here>
        Copyright (c) 2011

The copyright holders hereby grant to any person obtaining a copy of this software (the "Software") and/or its associated 
documentation files (the Documentation), the perpetual, irrevocable (except in the case of breach of this license) no-cost, 
royalty free, sublicensable rights to use, copy, modify, merge, publish, display, publicly perform, distribute, and/or 
sell copies of the Software and the Documentation, together or separately, and to permit persons to whom the Software and/or 
Documentation is furnished to do so, subject to the following conditions:

. Redistributions of the Software in source code must retain the above copyright notice, this list of conditions and the 
following disclaimers.

. Redistributions of the Software in binary form must reproduce the above copyright notice, this list of conditions and 
the following disclaimers in the documentation and/or other materials provided with the distribution.

. Redistributions of the Documentation must retain the above copyright notice, this list of conditions and the following 
disclaimers.

Neither the name of %(holder)s, nor the names of its contributors may be used to endorse or promote products derived from this
Software or the Documentation without specific prior written permission of the copyright holder.

THE SOFTWARE AND DOCUMENTATION ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT 
LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
CONTRIBUTORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, 
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR DOCUMENTATION OR THE USE OF OR OTHER 
DEALINGS WITH THE SOFTWARE OR DOCUMENTATION.
'''


readme = '''
%(longname)s
............

:Stable release:  eg 0.5.1, 1.1.3, unreleased

:Status:  eg, Feature complete, draft, idea, alpha

:Maintainer:  %(maintainer)s

Description
===========

%(description)s

Key Features
============

* <Bullet pointed list of features>

To Do
=====

* <Bullet pointed list of missing features>

Firmware Overview
=================

<One or more paragraphs detailing the functionality of modules and apps in this repo>

Known Issues
============

* <Bullet pointed list of problems>

Required Repositories
================

* <list of repos, likely to include xcommon if it uses the build system>
* xcommon git\@github.com:xcore/xcommon.git

Support
=======

<Description of support model>
'''


module_makefile = 'all:\n\t@echo "** Module only - only builds as part of application **"\n\n\nclean:\n\t@echo "** Module only - only builds as part of application **"\n\n\n'


documentation_dotproject = """<?xml version="1.0" encoding="UTF-8"?>
<projectDescription>
	<name>%PROJECT%</name>
	<comment></comment>
	<projects>
	</projects>
	<buildSpec>
	</buildSpec>
	<natures>
	</natures>
</projectDescription>
"""

makefile_include_str = '''
#=============================================================================
# The following part of the Makefile includes the common build infrastructure
# for compiling XMOS applications. You should not need to edit below here.

XMOS_MAKE_PATH ?= ../..
ifneq ($(wildcard $(XMOS_MAKE_PATH)/xcommon/module_xcommon/build/Makefile.common),)
include $(XMOS_MAKE_PATH)/xcommon/module_xcommon/build/Makefile.common
else
include ../module_xcommon/build/Makefile.common
endif


'''
