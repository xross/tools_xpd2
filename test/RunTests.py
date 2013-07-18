#! /usr/bin/env python

import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import shutil

from TestUtils import call, get_apps_from_github, get_parent
from XpdTest import *

ostype = platform.system()

def clean_repo(parent, folder):
    """ Put the test folder back into a known clean state
    """
    # Restore the git repo to not have any local files
    os.chdir(folder)
    call(['git', 'clean', '-xfdq'])
    call(['git', 'reset', 'HEAD'])
    call(['git', 'checkout', 'master'])

    # Delete all other cloned folders that aren't the folder in question
    for f in os.listdir(parent):
        fullname = os.path.join(parent, f)
        if not os.path.isdir(fullname) or (fullname == folder):
            continue
        shutil.rmtree(fullname)

def test_xpd_commands(top, folder):
    (parent, test_name) = os.path.split(folder)
    logging.info('Test: %s' % test_name)

    # Strip off the common bit of the path
    testname = folder[len(top):] + '_version'

    clean_repo(parent, folder)

    # Needs to get the version before getting dependencies as the
    # dependencies can change between versions
    (versions, errors) = call(['xpd', 'list'], cwd=folder)
    if not versions:
        logging.error('No versions')
        return

    # Ensure all versions can be checked out
    for version in versions[1:]:
        logging.info('Try: %s' % version)
        test_xpd_getdeps(folder, latest_version)
        call(['xpd', 'checkout', version])
        call(['xpd', 'status'])

    # xpd reverses the order of the releases so that the newest is the first
    latest_version = versions[0].rstrip()

    logging.info('Try: %s' % latest_version)
    test_xpd_getdeps(folder, latest_version)
    call(['xpd', 'checkout', latest_version])
    call(['xpd', 'status'])
    test_xpd_make_zip(folder)
    
    logging.info('Done: %s' % test_name)

def test_folder(top, folder):
    if os.path.isfile(os.path.join(folder, 'xpd.xml')):
        test_xpd_commands(top, folder)
        #test_xpd_latest(folder)
    else:
        for f in os.listdir(folder):
            if os.path.isdir(os.path.join(folder, f)):
                test_folder(top, os.path.join(folder, f))
                
def run_basic(tests_source_folder, tests_run_folder, test_name):
    logging.info('Running basic test %s' % test_name)
    src = os.path.join(tests_source_folder, test_name)
    dst = os.path.join(tests_run_folder, test_name)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    # Ensure the copied directory is a git repo with all files added 
    call(['git', 'init'], cwd=dst)
    call(['git', 'add', '.'], cwd=dst)
    call(['git', 'commit', '-m', '"Initial"'], cwd=dst)

    # Run the test
    test_xpd_init(dst)
    test_xpd_update(dst)

    # Check in everything after the update
    call(['git', 'commit', '-a', '-m', '"post update"'], cwd=dst)

def setup_logging(folder):
    """ Set up logging so only INFO and above go to the console but DEBUG and above go to
        a log file.
    """
    # Always open the file using 'wb' so that it is the same on Windows as other platforms
    logging.basicConfig(level=logging.DEBUG,
            format='%(levelname)-8s: %(message)s',
            filename=os.path.join(folder, 'tests.log'), filemode='wb')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

def run_basics(tests_source_folder, tests_run_folder):
    # Run the basic xpd functionality tests
    run_basic(tests_source_folder, tests_run_folder, 'test_basics_1')
    run_basic(tests_source_folder, tests_run_folder, 'test_basics_2')
    
    # Test creating a release which patches version numbers into defines
    test_folder = os.path.join(tests_run_folder, 'test_basics_2')
    test_xpd_create_release(test_folder, 'r', '1.2.3')
    call(['make'], cwd=test_folder)
    bin_path = os.path.join('app_test_basics_2_example', 'bin', 'app_test_basics_2_example.xe')
    (stdout_lines, stderr_lines) = call(['xsim', bin_path], cwd=test_folder)
    if ', '.join(stdout_lines) != "1, 2, 3, 1, 2, 3, 1.2.3, 1.2.3rc0":
        logging.error("Release patching failed")


def run_clone_xcore(tests_source_folder, tests_run_folder):
    logging.info("Cloning github repos to %s" % tests_run_folder)
    get_apps_from_github(tests_run_folder)

def run_test_all(tests_source_folder, tests_run_folder):
    logging.info("Running tests in %s" % tests_run_folder)
    test_folder(tests_run_folder, tests_run_folder)

def print_usage():
    (tests_source_folder, script_name) = os.path.split(os.path.realpath(__file__))
    print "%s: [TEST]+" % script_name
    print "  Available tests are: basics, clone_xcore, test_all"


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print_usage()

    setup_logging(os.getcwd())
    (tests_source_folder, script_name) = os.path.split(os.path.realpath(__file__))
    tests_run_folder = os.path.join(get_parent(get_parent(os.getcwd())), 'tests')
    logging.info("All tests running in %s" % tests_run_folder)

    for arg in sys.argv[1:]:
        run_fn = eval('run_%s' % arg)
        run_fn(tests_source_folder, tests_run_folder)

