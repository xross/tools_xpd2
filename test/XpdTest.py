#! /usr/bin/env python

import logging
import os
import platform
import re
import shutil
import subprocess
import sys

from TestUtils import *

def clean_repo(parent, folder):
    """ Put the test folder back into a known clean state
    """
    # Restore the git repo to not have any local files
    os.chdir(folder)
    call(["git", "clean", "-xfdq"])
    call(["git", "reset", "HEAD"])
    call(["git", "checkout", "master"])

    # Delete all other cloned folders that aren't the folder in question
    for f in os.listdir(parent):
        fullname = os.path.join(parent, f)
        if not os.path.isdir(fullname) or (fullname == folder):
            continue
        shutil.rmtree(fullname)

def test_xpd_version(top, folder):
    (parent, test_name) = os.path.split(folder)
    logging.info("Test: %s" % test_name)

    # Strip off the common bit of the path
    testname = folder[len(top):] + "_version"

    clean_repo(parent, folder)

    # Needs to get the version before getting dependencies as the
    # dependencies can change between versions
    (versions, errors) = call(["xpd", "list"], cwd=folder)
    if not versions:
        logging.error("No versions")
        return

    # Ensure all versions can be checked out
    for version in versions[1:]:
        logging.info("Try: %s" % version)
        call(["xpd", "getdeps", version])
        call(["xpd", "checkout", version])
        call(["xpd", "status"])

    # xpd reverses the order of the releases so that the newest is the first
    latest_version = versions[0].rstrip()

    logging.info("Try: %s" % latest_version)
    call(["xpd", "getdeps", latest_version])
    call(["xpd", "checkout", latest_version])
    call(["xpd", "status"])
    call(["xpd", "make_zip", latest_version])
    
    logging.info("Done: %s" % test_name)

def test_xpd_init(folder):
    (parent, test_name) = os.path.split(folder)
    logging.info("test_xpd_init: %s" % test_name)

    # Set of expected output from xpd init and the responses to give. It is built up
    # depending on the current state of the repo
    expected = []
    xpd_contents = []
    if os.path.exists(os.path.join(folder, 'xpd.xml')):
        with open(os.path.join(folder, 'xpd.xml')) as xpd:
            xpd_contents = xpd.readlines()

    if not any("<description>" in s for s in xpd_contents):
        expected += [Expect("No description found", "y"),
                     Expect("Enter paragraph description", "This is a test")]

    if not any("<vendor>" in s for s in xpd_contents):
        expected += [Expect("No vendor found", ""), # Test default value
                     Expect("Enter vendor name", "XMOS")]

    if not any("<maintainer>" in s for s in xpd_contents):
        expected += [Expect("No maintainer found", ""), # Test default value
                     Expect("Enter maintainer github username", "test")]

    if not any("<partnumber>" in s for s in xpd_contents):
        expected += [Expect("No part number found", "n")]

    apps = [f for f in os.listdir(folder) if f.startswith('app_')]
    if not apps:
        expected += [Expect("Would you like to create an application", "y"),
                     Expect("app_%s_example" % test_name, "")] # Test default value

    modules = [f for f in os.listdir(folder) if f.startswith('module_')]
    if not apps:
        expected += [Expect("Would you like to create an module", "y"),
                     Expect("module_%s_example" % test_name, "module_test")]

    if not os.path.exists(os.path.join(folder, 'LICENSE.txt')):
        expected += [Expect("Would you like to license the code", "y"),
                     Expect("Enter copyright holder", "XMOS")]

    interact(["xpd", "init"], expected, cwd=folder)

    check_exists('run_basics', [
            os.path.join(folder, 'xpd.xml'),
            os.path.join(folder, 'README.rst'), 
            os.path.join(folder, 'LICENSE.txt'),
            os.path.join(folder, 'Makefile'),
            os.path.join(folder, 'Makefile'),
            os.path.join(folder, 'app_%s_example' % test_name, 'README.rst'),
            os.path.join(folder, 'app_%s_example' % test_name, 'Makefile'),
            os.path.join(folder, 'app_%s_example' % test_name, 'src'),
            os.path.join(folder, 'module_test', 'README.rst'),
            os.path.join(folder, 'module_test', 'module_build_info'),
            os.path.join(folder, 'module_test', 'src')])

    logging.info("test_xpd_init: %s done" % test_name)

def test_xpd_update(folder):
    (parent, test_name) = os.path.split(folder)
    logging.info("test_xpd_update: %s" % test_name)

    # Set of expected output from xpd init and the responses to give. It is built up
    # depending on the current state of the repo
    expected = []
    xpd_contents = []
    if os.path.exists(os.path.join(folder, 'xpd.xml')):
        with open(os.path.join(folder, 'xpd.xml')) as xpd:
            xpd_contents = xpd.readlines()

    if not any("<partnumber>" in s for s in xpd_contents):
        expected += [Expect("No part number found", "n")]

    interact(["xpd", "update"], expected, cwd=folder)

    check_exists('run_basics', [
            os.path.join(folder, 'CHANGELOG.rst')])

    logging.info("test_xpd_update: %s done" % test_name)

def test_folder(top, folder):
    if os.path.isfile(os.path.join(folder, "xpd.xml")):
        test_xpd_version(top, folder)
        #test_xpd_latest(folder)
    else:
        for f in os.listdir(folder):
            if os.path.isdir(os.path.join(folder, f)):
                test_folder(top, os.path.join(folder, f))

def setup_logging(folder):
    """ Set up logging so only INFO and above go to the console but DEBUG and above go to
        a log file
    """
    logging.basicConfig(level=logging.DEBUG,
            format='%(asctime)s %(levelname)-8s: %(message)s',
            filename=os.path.join(folder, 'tests.log'), filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

if __name__ == "__main__":
    cwd = os.getcwd()
    setup_logging(cwd)
    test_folder(cwd, cwd)

