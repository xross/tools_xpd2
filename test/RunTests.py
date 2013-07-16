#! /usr/bin/env python

import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import shutil
import tempfile

from TestUtils import call, get_apps_from_github
from XpdTest import test_xpd_init, test_xpd_update

ostype = platform.system()

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
    test_name = os.path.split(folder)[-1]
    parent = os.path.sep.join(os.path.split(folder)[:-1])
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

def test_folder(top, folder):
    if os.path.isfile(os.path.join(folder, "xpd.xml")):
        test_xpd_version(top, folder)
        #test_xpd_latest(folder)
    else:
        for f in os.listdir(folder):
            if os.path.isdir(os.path.join(folder, f)):
                test_folder(top, os.path.join(folder, f))
                
def run_basics(tests_source_folder, tests_run_folder, test_name):
    logging.info("Running basic test %s" % test_name)
    src = os.path.join(tests_source_folder, test_name)
    dst = os.path.join(tests_run_folder, test_name)
    shutil.copytree(src, dst)

    call(["git", "init"], cwd=dst)
    test_xpd_init(dst)
    test_xpd_update(dst)

def setup_logging(folder):
    """ Set up logging so only INFO and above go to the console but DEBUG and above go to
        a log file.
    """
    # Always open the file using 'wb' so that it is the same on Windows as other platforms
    logging.basicConfig(level=logging.DEBUG,
            format='%(asctime)s %(levelname)-8s: %(message)s',
            filename=os.path.join(folder, 'tests.log'), filemode='wb')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


if __name__ == "__main__":
    setup_logging(os.getcwd())
    (tests_source_folder, script_name) = os.path.split(os.path.realpath(__file__))
    tests_run_folder = tempfile.mkdtemp()
    logging.info("All tests running in %s" % tests_run_folder)

    # Run the basic xpd functionality tests
    run_basics(tests_source_folder, tests_run_folder, 'test_basics_1')

#    logging.info("Cloning github repos to %s" % tests_run_folder)
#    get_apps_from_github(tests_run_folder)
#
#    logging.info("Running tests in %s" % tests_run_folder)
#    test_folder(cwd, cwd)

