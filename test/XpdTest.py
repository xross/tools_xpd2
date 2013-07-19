#! /usr/bin/env python

import logging
import os
import platform
import re
import shutil
import subprocess
import sys

from TestUtils import *

def test_xpd_build_docs(folder):
    (parent, test_name) = os.path.split(folder)
    logging.info("test_xpd_build_docs: %s" % test_name)
    xpd_contents = get_xpd_contents(folder)

    call(["xpd", "build_docs"])

    logging.info("test_xpd_build_docs: %s done" % test_name)

def test_xpd_make_zip(folder, user, password):
    (parent, test_name) = os.path.split(folder)
    logging.info("test_xpd_make_zip: %s" % test_name)
    xpd_contents = get_xpd_contents(folder)

    expected = [Expect(["Please enter cognidox username:"], [user]),
                Expect(["Password"], [password])]

    interact(["xpd", "make_zip"], expected, cwd=folder, early_out=True, timeout=120)

    logging.info("test_xpd_make_zip: %s done" % test_name)

def test_xpd_getdeps(folder, version=None):
    (parent, test_name) = os.path.split(folder)
    logging.info("test_xpd_getdeps: %s" % test_name)
    xpd_contents = get_xpd_contents(folder)
    deps = []
    for line in xpd_contents:
        m = re.search('<dependency repo = "(.*)"', line)
        if m:
            deps += [m.group(1)]

    if version:
        call(["xpd", "getdeps", version])
    else:
        call(["xpd", "getdeps"])

    check_exists([os.path.join(parent, dep) for dep in deps])

    logging.info("test_xpd_getdeps: %s done" % test_name)

def test_xpd_init(folder):
    """ Run xpd init. Expects different output depending on the current
        state of the repo that is having xpd init run on it.
    """
    (parent, test_name) = os.path.split(folder)
    logging.info("test_xpd_init: %s" % test_name)

    # Set of expected output from xpd init and the responses to give. It is built up
    # depending on the current state of the repo
    expected = []
    xpd_contents = get_xpd_contents(folder)

    if not any("<description>" in s for s in xpd_contents):
        expected += [Expect(["No description found"], ["y"]),
                     Expect(["Enter paragraph description"], ["This is a test"])]

    if not any("<vendor>" in s for s in xpd_contents):
        expected += [Expect(["No vendor found"], [""]), # Test default value
                     Expect(["Enter vendor name"], ["XMOS"])]

    if not any("<maintainer>" in s for s in xpd_contents):
        expected += [Expect(["No maintainer found"], [""]), # Test default value
                     Expect(["Enter maintainer github username"], ["test"])]

    if not any("<partnumber>" in s for s in xpd_contents):
        expected += [Expect(["No part number found"], ["n"])]

    apps = [f for f in os.listdir(folder) if f.startswith('app_')]
    if not apps:
        # xpd does some pre-processing on names it will use for the default app name
        default_name = test_name
        m = re.match('(proj_|sc_|sw_)(.*)', test_name)
        if m:
            default_name = m.group(2)

        expected += [Expect(["Would you like to create an application"], ["y"]),
                     Expect(["app_%s_example" % default_name], [""])] # Test default value

    modules = [f for f in os.listdir(folder) if f.startswith('module_')]
    if not modules:
        expected += [Expect(["Would you like to create a module"], ["y"]),
                     Expect(["Enter module name"], ["module_test_%s" % test_name[-1]])] # append last character

    if not os.path.exists(os.path.join(folder, 'LICENSE.txt')):
        expected += [Expect(["Would you like to license the code"], ["y"]),
                     Expect(["Enter copyright holder"], ["XMOS"])]

    (index, option) = interact(["xpd", "init"], expected, cwd=folder)

    expected_files = [os.path.join(folder, 'xpd.xml'),
                  os.path.join(folder, 'README.rst'), 
                  os.path.join(folder, 'LICENSE.txt'),
                  os.path.join(folder, 'Makefile')]

    for f in os.listdir(folder):
        if f.startswith('app_'):
            assert os.path.isdir(os.path.join(folder, f))
            expected_files += [os.path.join(folder, f, 'README.rst'),
                               os.path.join(folder, f, 'Makefile'),
                               os.path.join(folder, f, 'src')]
        if f.startswith('module_'):
            assert os.path.isdir(os.path.join(folder, f))
            expected_files += [os.path.join(folder, f, 'README.rst'),
                               os.path.join(folder, f, 'module_build_info'),
                               os.path.join(folder, f, 'src')]

    check_exists(expected_files)

    logging.info("test_xpd_init: %s done" % test_name)

def test_xpd_update(folder):
    """ Run xpd update and check that the required files all exist.
    """
    (parent, test_name) = os.path.split(folder)
    logging.info("test_xpd_update: %s" % test_name)

    # Set of expected output from xpd init and the responses to give. It is built up
    # depending on the current state of the repo
    expected = []
    xpd_contents = get_xpd_contents(folder)

    if not any("<partnumber>" in s for s in xpd_contents):
        expected += [Expect(["No part number found"], ["n"])]

    interact(["xpd", "update"], expected, cwd=folder)

    check_exists([os.path.join(folder, 'CHANGELOG.rst'),
                  os.path.join(folder, 'app_%s_example' % test_name, '.project'),
                  os.path.join(folder, 'app_%s_example' % test_name, '.cproject'),
                  os.path.join(folder, 'app_%s_example' % test_name, '.xproject'),
                  os.path.join(folder, 'module_test_%s' % test_name[-1], '.project'),
                  os.path.join(folder, 'module_test_%s' % test_name[-1], '.cproject'),
                  os.path.join(folder, 'module_test_%s' % test_name[-1], '.xproject'),
                  os.path.join(folder, 'module_test_%s' % test_name[-1], '.makefile')])

    logging.info("test_xpd_update: %s done" % test_name)

def test_xpd_create_release(folder, version_type, version_number):
    """ Test creating the specified release. If the create_release causes files to
        be modified then check that set of changes in and try again once. Any more
        changes after that are considered an error.
    """
    (parent, test_name) = os.path.split(folder)
    logging.info("test_xpd_create_release: %s" % test_name)

    # Set of expected output from xpd init and the responses to give. It is built up
    # depending on the current state of the repo
    expected = [Expect(["Enter release type"], [version_type]),
                Expect(["Enter version number"], [version_number]),
                Expect(["Create release %s" % version_number], [""]), # Use default answer
                Expect(["Are these notes up to date"], [""]), # Use default answer
                Expect(["Do you want to push the commit of this release upstream", "uncommitted modifications"], ["n", None], timeout=90)]
    xpd_contents = get_xpd_contents(folder)

    if not any("<partnumber>" in s for s in xpd_contents):
        expected += [Expect(["No part number found"], ["n"])]

    for i in range(2):
        (index, option) = interact(["xpd", "create_release"], expected, cwd=folder, early_out=True)

        # Detect the case where modifications were created by the 'create_release'
        if i and option:
            logging.error("xpd created modifications on second iteration")
        elif option:
            # Commit the changes and try again
            call(['git', 'commit', '-a', '-m', '"xpd"'], cwd=folder)
        else:
            break

    logging.info("test_xpd_create_release: %s done" % test_name)

