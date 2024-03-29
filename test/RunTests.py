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
        log_debug('Added version %s to changelog (%s)' % (version, folder))
    except:
        log_error('Error patching CHANGELOG.rst', exc_info=True)

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
        log_debug('%s disconnected from remote git' % folder)
    except:
        log_error('Error modifying .git/config', exc_info=True)

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
        log_debug('%s re-connected to remote git' % folder)
    except:
        log_error('Error modifying .git/config', exc_info=True)

def clean_repo(parent, folder):
    """ Put the test folder back into a known clean state
    """
    log_debug('Clean %s, %s' % (parent, folder))
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
        log_debug('rmtree %s' % fullname)
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
    versions = [line.rstrip() for line in stdout_lines + stderr_lines if
                    not re.search('WARNING', line) and not re.search('ERROR', line)]
    if not versions:
        log_warning('No versions')
        return

    break_remote_link(folder)

    # Ensure all versions can be checked out
    for version in versions[1:]:
        log_info('Try: %s' % version)
        test_xpd_get_deps(folder, version)
        call(['xpd', 'checkout', version])
        call(['xpd', 'status'])

    # xpd reverses the order of the releases so that the newest is the first
    latest_version = versions[0]

    log_info('Try: %s' % latest_version)
    test_xpd_get_deps(folder, latest_version)
    call(['xpd', 'checkout', latest_version])
    call(['xpd', 'status'])
    call(['xpd', 'check_deps'])
    test_xpd_update(folder)
    test_xpd_make_zip(folder, args.user, args.password)

    # Try creating a release of the master
    test_xpd_get_deps(folder, 'master')
    call(['xpd', 'checkout', 'master'])
    patch_changelog(folder, '100.200.300')
    call(['git', 'commit', '-a', '-m', '"updated changelog"'], cwd=folder)

    # Test a beta release
    test_xpd_create_release(folder, 'b', '100.200.300')

    # And a release candidate
    test_xpd_create_release(folder, 'r', '100.200.300')

    test_xpd_command(folder, 'build_docs')
    
    restore_remote_link(folder)

    log_info('Done: %s' % test_name)

def create_basic(tests_source_folder, tests_run_folder, test_name):
    log_info('Creating basic test %s' % test_name)
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

def run_basic(tests_run_folder, test_name):
    dst_folder = os.path.join(tests_run_folder, 'test_%s' % test_name)
    dst = os.path.join(dst_folder, test_name)

    log_info('Running basic test %s' % test_name)
    # Run the test
    test_xpd_init(dst)
    test_xpd_update(dst)

    # Check in everything after the update
    call(['git', 'commit', '-a', '-m', '"post update"'], cwd=dst)

def run_basics_1(tests_source_folder, tests_run_folder):
    # Run the basic xpd functionality tests
    create_basic(tests_source_folder, tests_run_folder, 'basics_1')
    run_basic(tests_run_folder, 'basics_1')

def run_basics_2(tests_source_folder, tests_run_folder):
    create_basic(tests_source_folder, tests_run_folder, 'basics_2')
    run_basic(tests_run_folder, 'basics_2')
    
    # Test creating a release which patches version numbers into defines
    folder = os.path.join(tests_run_folder, 'test_basics_2', 'basics_2')
    test_xpd_create_release(folder, 'r', '1.2.3')
    call(['make'], cwd=folder)
    bin_path = os.path.join('app_basics_2_example', 'bin', 'app_basics_2_example.xe')
    (stdout_lines, stderr_lines) = call(['xsim', bin_path], cwd=folder)
    if ', '.join(stdout_lines) != '1, 2, 3, 1, 2, 3, 1.2.3, 1.2.3rc0':
        log_error('Release patching failed')

def run_basics_3(tests_source_folder, tests_run_folder):
    # Test that xpd correctly detects errors in xpd.xml
    expected_errors = ['ERROR: [^ ]+xpd.xml:4:8: Missing attribute description',
                       'ERROR: [^ ]+xpd.xml:4:8: Missing attribute scope',
                       'ERROR: [^ ]+xpd.xml:8:8: Missing attribute id',
                       'ERROR: [^ ]+xpd.xml:8:8: Missing attribute path',
                       'ERROR: [^ ]+xpd.xml:11:4: Missing attribute repo',
                       'ERROR: [^ ]+xpd.xml:11:4: Missing node githash',
                       'ERROR: [^ ]+xpd.xml:11:4: Missing node uri',
                       'ERROR: No git repo found in [^ ]+test_basics_3' # The lack of a uri causes this error
                    ]

    create_basic(tests_source_folder, tests_run_folder, 'basics_3')
    test_folder = os.path.join(tests_run_folder, 'test_basics_3', 'basics_3')

    # Use the generic 'test_xpd_command' function because the errors in the repo
    # mean the interaction won't occur
    set_ignore_errors(True)
    output = test_xpd_update(test_folder)
    set_ignore_errors(False)
    check_all_errors_seen_and_expected(output, expected_errors)

    # Fix the xpd.xml errors by removing the <dependency>, </dependency> lines
    lines = []
    with open(os.path.join(test_folder, 'xpd.xml'), 'r') as f:
        lines = f.readlines()
    with open(os.path.join(test_folder, 'xpd.xml'), 'wb') as f:
        for line in lines:
            if not re.search('dependency', line):
                f.write(line)

    call(['git', 'add', 'xpd.xml'], cwd=test_folder)
    call(['git', 'commit', '-m', '"Removed dependency"'], cwd=test_folder)

    test_xpd_update(test_folder)
    call(['git', 'add', 'xpd.xml'], cwd=test_folder)
    call(['git', 'commit', '-m', '"Update fixed missing required attributes"'], cwd=test_folder)

    # Now try running build_docs as that should have some other errors
    expected_errors = ["ERROR: basics_3: xsoftip_exclude 'not_a_folder' does not exist",
                       "ERROR: basics_3: docdir 'not_a_docdir' does not exist",
                       "ERROR: basics_3: Missing top-level README.rst"]

    set_ignore_errors(True)
    output = test_xpd_command(test_folder, 'build_docs')
    set_ignore_errors(False)
    check_all_errors_seen_and_expected(output, expected_errors)

def run_basics(tests_source_folder, tests_run_folder, args):
    run_basics_1(tests_source_folder, tests_run_folder)
    run_basics_2(tests_source_folder, tests_run_folder)
    run_basics_3(tests_source_folder, tests_run_folder)

def run_clone_xcore(tests_source_folder, tests_run_folder, args):
    log_info("Cloning github repos to %s" % tests_run_folder)
    get_apps_from_github(tests_run_folder)

def run_test_all(tests_source_folder, tests_run_folder, args):
    log_info("Running tests in %s" % tests_run_folder)
#    test_xpd_commands(os.path.join(tests_run_folder, 'test_sw_avb', 'sw_avb'), args)
#    return

    for folder in os.listdir(tests_run_folder):
        if not os.path.isdir(os.path.join(tests_run_folder, folder)) or not folder.startswith('test_'):
            continue

        # Tests should be of the form test_x/x/
        subfolder = re.sub('^test_', '', folder)
        if not os.path.isdir(os.path.join(tests_run_folder, folder, subfolder)):
            continue

        test_xpd_commands(os.path.join(tests_run_folder, folder, subfolder), args)

supported_tests = ['basics', 'clone_xcore', 'test_all']

def print_usage():
    (tests_source_folder, script_name) = os.path.split(os.path.realpath(__file__))
    print '%s: [TEST]+' % script_name
    print '  Available tests are: %s' % ', '.join(supported_tests)
    sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Automated test')
    parser.add_argument('user', help='cognidox user')
    parser.add_argument('password', help='cognidox password')
    parser.add_argument('tests', nargs='+', help='tests', choices=supported_tests)
    args = parser.parse_args()

    setup_logging(os.getcwd())
    (tests_source_folder, script_name) = os.path.split(os.path.realpath(__file__))
    tests_run_folder = os.path.join(get_parent(get_parent(os.getcwd())), 'tests')
    if not os.path.isdir(tests_run_folder):
        os.mkdir(tests_run_folder)
    log_info('Tests running in %s' % tests_run_folder)

    for arg in args.tests:
        run_fn = eval('run_%s' % arg)
        run_fn(tests_source_folder, tests_run_folder, args)

    print_summary()

