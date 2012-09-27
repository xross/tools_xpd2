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
# not includse the .xe postfix. If left blank the name will default to
# the project name
APP_NAME =

# The USED_MODULES variable lists other module used by the application.
USED_MODULES =

# The flags passed to xcc when building the application
# You can also set the following to override flags for a particular language:
# XCC_XC_FLAGS, XCC_C_FLAGS, XCC_ASM_FLAGS, XCC_CPP_FLAGS
# If the variable XCC_MAP_FLAGS is set it overrides the flags passed to
# xcc for the final link (mapping) stage.
XCC_FLAGS = -g -O3

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
            <storageModule moduleId="org.eclipse.cdt.make.core.buildtargets">
                <buildTargets>
                    <target name="all" path=""
targetID="org.eclipse.cdt.build.MakeTargetBuilder">
                        <buildCommand>xmake</buildCommand>
                        <buildArguments>%CONFIG_ARGS%</buildArguments>
                        <buildTarget>all</buildTarget>
                        <stopOnError>true</stopOnError>
                        <useDefaultCommand>true</useDefaultCommand>
                        <runAllBuilders>true</runAllBuilders>
                    </target>
                    <target name="clean" path=""
targetID="org.eclipse.cdt.build.MakeTargetBuilder">
                        <buildCommand>xmake</buildCommand>
                        <buildArguments>%CONFIG_ARGS%</buildArguments>
                        <buildTarget>clean</buildTarget>
                        <stopOnError>true</stopOnError>
                        <useDefaultCommand>true</useDefaultCommand>
                        <runAllBuilders>true</runAllBuilders>
                    </target>
                </buildTargets>
            </storageModule>
            <storageModule moduleId="cdtBuildSystem" version="4.0.0">
                <configuration buildProperties="" description="" id="com.xmos.cdt.toolchain.%CONFIG_ID%" name="%CONFIG%" parent="org.eclipse.cdt.build.core.emptycfg">
                    <folderInfo id="com.xmos.cdt.toolchain.%CONFIG_ID%.1127281840" name="/" resourcePath="">
                        <toolChain id="com.xmos.cdt.toolchain.1842437102" name="com.xmos.cdt.toolchain" superClass="com.xmos.cdt.toolchain">
                            <targetPlatform archList="all" binaryParser="com.xmos.cdt.core.XEBinaryParser" id="com.xmos.cdt.core.platform.942407365" isAbstract="false" osList="linux,win32,macosx" superClass="com.xmos.cdt.core.platform" />
                            <builder arguments="%CONFIG_ARGS%" id="com.xmos.cdt.builder.base.2141163380" keepEnvironmentInBuildfile="false" managedBuildOn="false" superClass="com.xmos.cdt.builder.base">
                                <outputEntries>
                                    <entry flags="VALUE_WORKSPACE_PATH" kind="outputPath" name="%CONFIG_OUTPUT_DIR%" />
                                </outputEntries>
                            </builder>
                            <tool id="com.xmos.cdt.xc.compiler.73393562" name="com.xmos.cdt.xc.compiler" superClass="com.xmos.cdt.xc.compiler">
	<option id="com.xmos.c.compiler.option.defined.symbols.379709232" name="com.xmos.c.compiler.option.defined.symbols" superClass="com.xmos.c.compiler.option.defined.symbols" valueType="definedSymbols">
									<listOptionValue builtIn="false" value="__SHRT_MAX__=32767"/>
									<listOptionValue builtIn="false" value="__SCHAR_MAX__=127"/>
									<listOptionValue builtIn="false" value="__SIZE_TYPE__=unsigned"/>
									<listOptionValue builtIn="false" value="__WCHAR_TYPE__=unsigned"/>
									<listOptionValue builtIn="false" value="__STDC_HOSTED__=1"/>
									<listOptionValue builtIn="false" value="XCC_VERSION_YEAR=11"/>
									<listOptionValue builtIn="false" value="__PTRDIFF_TYPE__=int"/>
									<listOptionValue builtIn="false" value="XCC_VERSION_MAJOR=1111"/>
									<listOptionValue builtIn="false" value="XCC_VERSION_MINOR=1"/>
									<listOptionValue builtIn="false" value="XCC_VERSION_MONTH=11"/>
									<listOptionValue builtIn="false" value="__CHAR_UNSIGNED__=1"/>
									<listOptionValue builtIn="false" value="__MCPP=2"/>
									<listOptionValue builtIn="false" value="__XC__=1"/>
									<listOptionValue builtIn="false" value="__XS1B__=1"/>
									<listOptionValue builtIn="false" value="__INT_MAX__=2147483647"/>
									<listOptionValue builtIn="false" value="__LONG_MAX__=2147483647L"/>
									<listOptionValue builtIn="false" value="__STDC__=1"/>
									<listOptionValue builtIn="false" value="__GNUC__=4"/>
									<listOptionValue builtIn="false" value="__GNUC_MINOR__=2"/>
									<listOptionValue builtIn="false" value="__GNUC_PATCHLEVEL__=1"/>
									<listOptionValue builtIn="false" value="__llvm__=1"/>
									<listOptionValue builtIn="false" value="__WINT_TYPE__=unsigned"/>
									<listOptionValue builtIn="false" value="__INTMAX_TYPE__=long"/>
									<listOptionValue builtIn="false" value="__UINTMAX_TYPE__=long"/>
									<listOptionValue builtIn="false" value="__GXX_ABI_VERSION=1002"/>
									<listOptionValue builtIn="false" value="__LONG_LONG_MAX__=9223372036854775807LL"/>
									<listOptionValue builtIn="false" value="__WCHAR_MAX__=255U"/>
									<listOptionValue builtIn="false" value="__CHAR_BIT__=8"/>
									<listOptionValue builtIn="false" value="__INTMAX_MAX__=9223372036854775807LL"/>
									<listOptionValue builtIn="false" value="__FLT_EVAL_METHOD__=0"/>
									<listOptionValue builtIn="false" value="__DEC_EVAL_METHOD__=2"/>
									<listOptionValue builtIn="false" value="__FLT_RADIX__=2"/>
									<listOptionValue builtIn="false" value="__FLT_MANT_DIG__=24"/>
									<listOptionValue builtIn="false" value="__FLT_DIG__=6"/>
									<listOptionValue builtIn="false" value="__FLT_MIN_EXP__=(-125)"/>
									<listOptionValue builtIn="false" value="__FLT_MIN_10_EXP__=(-37)"/>
									<listOptionValue builtIn="false" value="__FLT_MAX_EXP__=128"/>
									<listOptionValue builtIn="false" value="__FLT_MAX_10_EXP__=38"/>
									<listOptionValue builtIn="false" value="__FLT_MAX__=3.40282347e+38F"/>
									<listOptionValue builtIn="false" value="__FLT_MIN__=1.17549435e-38F"/>
									<listOptionValue builtIn="false" value="__FLT_EPSILON__=1.19209290e-7F"/>
									<listOptionValue builtIn="false" value="__FLT_DENORM_MIN__=1.40129846e-45F"/>
									<listOptionValue builtIn="false" value="__FLT_HAS_DENORM__=1"/>
									<listOptionValue builtIn="false" value="__FLT_HAS_INFINITY__=1"/>
									<listOptionValue builtIn="false" value="__FLT_HAS_QUIET_NAN__=1"/>
									<listOptionValue builtIn="false" value="__DBL_MANT_DIG__=53"/>
									<listOptionValue builtIn="false" value="__DBL_DIG__=15"/>
									<listOptionValue builtIn="false" value="__DBL_MIN_EXP__=(-1021)"/>
									<listOptionValue builtIn="false" value="__DBL_MIN_10_EXP__=(-307)"/>
									<listOptionValue builtIn="false" value="__DBL_MAX_EXP__=1024"/>
									<listOptionValue builtIn="false" value="__DBL_MAX_10_EXP__=308"/>
									<listOptionValue builtIn="false" value="__DBL_MAX__=1.7976931348623157e+308"/>
									<listOptionValue builtIn="false" value="__DBL_MIN__=2.2250738585072014e-308"/>
									<listOptionValue builtIn="false" value="__DBL_EPSILON__=2.2204460492503131e-16"/>
									<listOptionValue builtIn="false" value="__DBL_DENORM_MIN__=4.9406564584124654e-324"/>
									<listOptionValue builtIn="false" value="__DBL_HAS_DENORM__=1"/>
									<listOptionValue builtIn="false" value="__DBL_HAS_INFINITY__=1"/>
									<listOptionValue builtIn="false" value="__DBL_HAS_QUIET_NAN__=1"/>
									<listOptionValue builtIn="false" value="__LDBL_MANT_DIG__=53"/>
									<listOptionValue builtIn="false" value="__LDBL_DIG__=15"/>
									<listOptionValue builtIn="false" value="__LDBL_MIN_EXP__=(-1021)"/>
									<listOptionValue builtIn="false" value="__LDBL_MIN_10_EXP__=(-307)"/>
									<listOptionValue builtIn="false" value="__LDBL_MAX_EXP__=1024"/>
									<listOptionValue builtIn="false" value="__LDBL_MAX_10_EXP__=308"/>
									<listOptionValue builtIn="false" value="__DECIMAL_DIG__=17"/>
									<listOptionValue builtIn="false" value="__LDBL_MAX__=1.7976931348623157e+308L"/>
									<listOptionValue builtIn="false" value="__LDBL_MIN__=2.2250738585072014e-308L"/>
									<listOptionValue builtIn="false" value="__LDBL_EPSILON__=2.2204460492503131e-16L"/>
									<listOptionValue builtIn="false" value="__LDBL_DENORM_MIN__=4.9406564584124654e-324L"/>
									<listOptionValue builtIn="false" value="__LDBL_HAS_DENORM__=1"/>
									<listOptionValue builtIn="false" value="__LDBL_HAS_INFINITY__=1"/>
									<listOptionValue builtIn="false" value="__LDBL_HAS_QUIET_NAN__=1"/>
									<listOptionValue builtIn="false" value="__DEC32_MANT_DIG__=7"/>
									<listOptionValue builtIn="false" value="__DEC32_MIN_EXP__=(-95)"/>
									<listOptionValue builtIn="false" value="__DEC32_MAX_EXP__=96"/>
									<listOptionValue builtIn="false" value="__DEC32_MIN__=1E-95DF"/>
									<listOptionValue builtIn="false" value="__DEC32_MAX__=9.999999E96DF"/>
									<listOptionValue builtIn="false" value="__DEC32_EPSILON__=1E-6DF"/>
									<listOptionValue builtIn="false" value="__DEC32_DEN__=0.000001E-95DF"/>
									<listOptionValue builtIn="false" value="__DEC64_MANT_DIG__=16"/>
									<listOptionValue builtIn="false" value="__DEC64_MIN_EXP__=(-383)"/>
									<listOptionValue builtIn="false" value="__DEC64_MAX_EXP__=384"/>
									<listOptionValue builtIn="false" value="__DEC64_MIN__=1E-383DD"/>
									<listOptionValue builtIn="false" value="__DEC64_MAX__=9.999999999999999E384DD"/>
									<listOptionValue builtIn="false" value="__DEC64_EPSILON__=1E-15DD"/>
									<listOptionValue builtIn="false" value="__DEC64_DEN__=0.000000000000001E-383DD"/>
									<listOptionValue builtIn="false" value="__DEC128_MANT_DIG__=34"/>
									<listOptionValue builtIn="false" value="__DEC128_MIN_EXP__=(-6143)"/>
									<listOptionValue builtIn="false" value="__DEC128_MAX_EXP__=6144"/>
									<listOptionValue builtIn="false" value="__DEC128_MIN__=1E-6143DL"/>
									<listOptionValue builtIn="false" value="__DEC128_MAX__=9.999999999999999999999999999999999E6144DL"/>
									<listOptionValue builtIn="false" value="__DEC128_EPSILON__=1E-33DL"/>
									<listOptionValue builtIn="false" value="__DEC128_DEN__=0.000000000000000000000000000000001E-6143DL"/>
									<listOptionValue builtIn="false" value="__REGISTER_PREFIX__"/>
									<listOptionValue builtIn="false" value="__USER_LABEL_PREFIX__"/>
									<listOptionValue builtIn="false" value="__VERSION__=&quot;4.2.1"/>
									<listOptionValue builtIn="false" value="__GNUC_GNU_INLINE__=1"/>
									<listOptionValue builtIn="false" value="__BLOCKS__=1"/>
									<listOptionValue builtIn="false" value="__NO_INLINE__=1"/>
									<listOptionValue builtIn="false" value="__FINITE_MATH_ONLY__=0"/>
									<listOptionValue builtIn="false" value="__ELF__=1"/>
									<listOptionValue builtIn="false" value="__XCC_HAVE_FLOAT__=1"/>
									<listOptionValue builtIn="false" value="__cplusplus=1"/>
									<listOptionValue builtIn="false" value="__GNUG__=4"/>
									<listOptionValue builtIn="false" value="__GXX_WEAK__=1"/>
									<listOptionValue builtIn="false" value="__DEPRECATED=1"/>
									<listOptionValue builtIn="false" value="__EXCEPTIONS=1"/>
									<listOptionValue builtIn="false" value="__WCHAR_UNSIGNED__=1"/>
								</option>

                                <option id="com.xmos.c.compiler.option.include.paths.569332846" name="com.xmos.c.compiler.option.include.paths" superClass="com.xmos.c.compiler.option.include.paths" valueType="includePath">
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/gcc&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1&quot;' />
                                    <listOptionValue builtIn="false" value='&quot;${XMOS_DOC_PATH}/../target/include/c++/4.2.1/xcore-xmos-elf&quot;' />
                                    %INCLUDES%
                                </option>
                                <inputType id="com.xmos.cdt.xc.compiler.input.1177118008" name="XC Sources" superClass="com.xmos.cdt.xc.compiler.input" />
                                <option id="gnu.c.compiler.option.include.paths.11111" valueType="includePath" superClass="gnu.c.compiler.option.include.paths">
                                    %INCLUDES%
                                </option>
                            </tool>
                            <tool id="com.xmos.cdt.xc.compiler.base.11111" name="com.xmos.cdt.xc.compiler.base" superClass="com.xmos.cdt.xc.compiler.base">
                                <option id="gnu.c.compiler.option.include.paths.11111" valueType="includePath" superClass="gnu.c.compiler.option.include.paths">
                                    %INCLUDES%
                                </option>
                                <option id="com.xmos.c.compiler.option.include.paths.11111" valueType="includePath" superClass="com.xmos.c.compiler.option.include.paths">
                                    %INCLUDES%
                                </option>
                            </tool>
                            <tool id="com.xmos.cdt.c.compiler.base.11111" name="com.xmos.cdt.c.compiler.base" superClass="com.xmos.cdt.c.compiler.base">
                                <option id="gnu.c.compiler.option.include.paths.11111" valueType="includePath" superClass="gnu.c.compiler.option.include.paths">
                                    %INCLUDES%
                                </option>
                                <option id="com.xmos.c.compiler.option.include.paths.11111" valueType="includePath" superClass="com.xmos.c.compiler.option.include.paths">
                                    %INCLUDES%
                                </option>
                            </tool>
                            <tool id="com.xmos.cdt.cpp.compiler.base.11111" name="com.xmos.cdt.cpp.compiler.base" superClass="com.xmos.cdt.cpp.compiler.base">
                                <option id="gnu.c.compiler.option.include.paths.11111" valueType="includePath" superClass="gnu.c.compiler.option.include.paths">
                                    %INCLUDES%
                                </option>
                                <option id="com.xmos.c.compiler.option.include.paths.11111" valueType="includePath" superClass="com.xmos.c.compiler.option.include.paths">
                                    %INCLUDES%
                                </option>
                            </tool>
                            <tool id="com.xmos.cdt.core.assembler.base.11111" name="com.xmos.cdt.core.assembler.base" superClass="com.xmos.cdt.core.assembler.base">
                                <option id="gnu.c.compiler.option.include.paths.11111" valueType="includePath" superClass="gnu.c.compiler.option.include.paths">
                                    %INCLUDES%
                                </option>
                                <option id="com.xmos.c.compiler.option.include.paths.11111" valueType="includePath" superClass="com.xmos.c.compiler.option.include.paths">
                                    %INCLUDES%
                                </option>
                            </tool>

                        </toolChain>
                    </folderInfo>
                    <sourceEntries>
                        <entry excluding=".build_*" flags="VALUE_WORKSPACE_PATH|RESOLVED"
                    kind="sourcePath" name="" />
                    </sourceEntries>
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
			<name>com.xmos.cdt.core.ModulePathBuilder</name>
			<arguments>
			</arguments>
		</buildCommand>
		<buildCommand>
			<name>org.eclipse.cdt.managedbuilder.core.genmakebuilder</name>
			<triggers>clean,full,incremental,</triggers>
			<arguments>
				<dictionary>
					<key>?children?</key>
					<value>?name?=outputEntries\|?children?=?name?=entry\\\\\\\|\\\|\||</value>
				</dictionary>
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

extra_project_makefile = 'all:\n\t@echo "** This project has no build **\n\n\nclean:\n\t@echo "** This project has no build **"\n\n\n'

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

swblock_readme = '''\
<Add title here>
================

:scope: <Put one of Roadmap, Example, Early Development or General Use>
:description: <Add one line here>
:keywords: <Add comma separated list of keywords>
:boards: <Add comma separated list of supported boards>

<Add description of software block>
'''

changelog = '''\
<Insert Repo name> Change Log
=============================

1.1.0
-----
  * Bullet points of features
  * Another point
  * ...

1.0.0
-----
  * Initial Version
'''


