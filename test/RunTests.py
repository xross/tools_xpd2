#! /usr/bin/env python

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import shutil

from TestUtils import *
from XpdTest import *

ostype = platform.system()

def patch_changelog(folder, version):
    """ Patch the changelog with a version so that a release can be created.
        Create the changelog file if it is missing.
    """
    changelog_path = os.path.join(folder, 'CHANGELOG.rst')
    if not os.path.exists(changelog_path):
        log_error('CHANGELOG.rst missing')
        with open(changelog_path, 'wb') as f:
            (parent, test_name) = os.path.split(folder)
            title = '%s Change Log' % test_name
            f.write(title + '\n')
            f.write('%s\n' % '=' * len(title))

        call(['git', 'add', 'CHANGELOG.rst'], cwd=folder)
        call(['git', 'commit', '-m', '"Added change log"'], cwd=folder)

    try:
        lines = []
        with open(changelog_path, 'r') as f:
            lines = f.readlines()
        with open(changelog_path, 'wb') as f:
            for line in lines[0:3]:
                f.write(line)
            f.write('%s\n' % version)
            f.write('%s\n' % ('-' * len(version)))
            f.write('  * Test release\n')
            f.write('\n')
            for line in lines[3:]:
                f.write(line)
        log_debug("Added version %s to changelog (%s)" % (version, folder))
    except:
        log_error("Error patching CHANGELOG.rst", exc_info=True)

def break_remote_link(folder):
    """ Break the 'url' line of the .git/config file so that the testing cannot
        accidentally push to the remote repo.
    """
    try:
        lines = []
        with open(os.path.join(folder, '.git', 'config'), 'r') as f:
            lines = f.readlines()
        with open(os.path.join(folder, '.git', 'config'), 'wb') as f:
            for line in lines:
                if re.search('^\s*url = ', line):
                    f.write('#')
                f.write(line)
        log_debug("%s disconnected from remote git" % folder)
    except:
        log_error("Error modifying .git/config", exc_info=True)

def restore_remote_link(folder):
    """ Restore the 'url' line of the .git/config file so that the repo can
        be updated.
    """
    try:
        lines = []
        with open(os.path.join(folder, '.git', 'config'), 'r') as f:
            lines = f.readlines()
        with open(os.path.join(folder, '.git', 'config'), 'wb') as f:
            for line in lines:
                if re.match('^#(\s*url = .*)$', line):
                    line = line[1:]
                f.write(line)
        log_debug("%s re-connected to remote git" % folder)
    except:
        log_error("Error modifying .git/config", exc_info=True)

def clean_repo(parent, folder):
    """ Put the test folder back into a known clean state
    """
    log_debug("Clean %s, %s" % (parent, folder))
    # Restore the git repo to not have any local files - need all the
    # commands due to some being only local repos and therefore not
    # having an origin/master
    os.chdir(folder)
    call(['git', 'clean', '-xfdq'])
    
    if git_has_origin(folder):
        call(['git', 'fetch', 'origin'])
        call(['git', 'reset', '--hard', 'origin/master'])
    else:
        call(['git', 'checkout', '--', '.'])

    # Delete all other cloned folders that aren't the folder in question
    for f in os.listdir(parent):
        fullname = os.path.join(parent, f)
        if not os.path.isdir(fullname) or (fullname == folder):
            continue
        log_debug("rmtree %s" % fullname)
        shutil.rmtree(fullname)

def test_xpd_commands(folder, args):
    (parent, test_name) = os.path.split(folder)
    log_info('Test: %s' % test_name)

    # Ensure things start in a clean state
    clean_repo(parent, folder)

    # Test xpd init doesn't break - ensuring that there is no way it can get pushed
    break_remote_link(folder)
    test_xpd_init(folder)
    restore_remote_link(folder)

    # Undo any changes from xpd init
    clean_repo(parent, folder)

    # Needs to get the version before getting dependencies as the
    # dependencies can change between versions
    (stdout_lines, stderr_lines) = call(['xpd', 'list'], cwd=folder)
    versions = [line.rstrip() for line in stdout_lines + stderr_lines]
    if not versions:
        log_warning('No versions')
        return

    break_remote_link(folder)

    # Ensure all versions can be checked out
    for version in versions[1:]:
        log_info('Try: %s' % version)
        test_xpd_getdeps(folder, version)
        call(['xpd', 'checkout', version])
        call(['xpd', 'status'])

    # xpd reverses the order of the releases so that the newest is the first
    latest_version = versions[0]

    log_info('Try: %s' % latest_version)
    test_xpd_getdeps(folder, latest_version)
    call(['xpd', 'checkout', latest_version])
    call(['xpd', 'status'])
    test_xpd_make_zip(folder, args.user, args.password)

    # Try creating a release of the master
    test_xpd_getdeps(folder, 'master')
    call(['xpd', 'checkout', 'master'])
    patch_changelog(folder, '100.200.300')
    call(['git', 'commit', '-a', '-m', '"updated changelog"'], cwd=folder)

    test_xpd_create_release(folder, 'b', '100.200.300')

    test_xpd_build_docs(folder)
    
    restore_remote_link(folder)


def test_folders(top):
    for folder in os.listdir(top):
        if not os.path.isdir(os.path.join(top, folder)) or not folder.startswith('test_'):
            continue

        # Tests should be of the form test_x/x/
        subfolder = re.sub('^test_', '', folder)
        if not os.path.isdir(os.path.join(top, folder, subfolder)):
            continue

        test_xpd_commands(os.path.join(top, folder, subfolder))
    log_info('Done: %s' % test_name)

def run_basic(tests_source_folder, tests_run_folder, test_name):
    log_info('Running basic test %s' % test_name)
    src = os.path.join(tests_source_folder, 'test_%s' % test_name, test_name)
    dst_folder = os.path.join(tests_run_folder, 'test_%s' % test_name)
    dst = os.path.join(dst_folder, test_name)

    if os.path.exists(dst):
        shutil.rmtree(dst)
    if not os.path.exists(dst_folder):
        os.mkdir(dst_folder)
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

def run_basics(tests_source_folder, tests_run_folder, args):
    # Run the basic xpd functionality tests
    run_basic(tests_source_folder, tests_run_folder, 'basics_1')
    run_basic(tests_source_folder, tests_run_folder, 'basics_2')
    
    # Test creating a release which patches version numbers into defines
    folder = os.path.join(tests_run_folder, 'test_basics_2', 'basics_2')
    test_xpd_create_release(folder, 'r', '1.2.3')
    call(['make'], cwd=folder)
    bin_path = os.path.join('app_basics_2_example', 'bin', 'app_basics_2_example.xe')
    (stdout_lines, stderr_lines) = call(['xsim', bin_path], cwd=folder)
    if ', '.join(stdout_lines) != "1, 2, 3, 1, 2, 3, 1.2.3, 1.2.3rc0":
        log_error("Release patching failed")

def run_clone_xcore(tests_source_folder, tests_run_folder, args):
    log_info("Cloning github repos to %s" % tests_run_folder)
    get_apps_from_github(tests_run_folder)

def run_test_all(tests_source_folder, tests_run_folder, args):
    logging.info("Running tests in %s" % tests_run_folder)
    test_folders(tests_run_folder)

supported_tests = ['basics', 'clone_xcore', 'test_all']

def print_usage():
    (tests_source_folder, script_name) = os.path.split(os.path.realpath(__file__))
    print "%s: [TEST]+" % script_name
    print "  Available tests are: %s" % ', '.join(supported_tests)
    sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Automated test')
    parser.add_argument('user', help="cognidox user")
    parser.add_argument('password', help="cognidox password")
    parser.add_argument('tests', nargs='+', help='tests', choices=supported_tests)
    args = parser.parse_args()

    setup_logging(os.getcwd())
    (tests_source_folder, script_name) = os.path.split(os.path.realpath(__file__))
    tests_run_folder = os.path.join(get_parent(get_parent(os.getcwd())), 'tests')
    log_info("Tests running in %s" % tests_run_folder)

    for arg in args.tests:
        run_fn = eval('run_%s' % arg)
        run_fn(tests_source_folder, tests_run_folder, args)

    print_summary()

