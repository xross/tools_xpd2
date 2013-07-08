#! /usr/bin/env python

import logging
import os
import platform
import re
import shutil
import subprocess
import sys

ostype = platform.system()

if not re.match('.*Darwin.*', ostype) and re.match('.*[W|w]in.*', ostype):
    concat_args = True
    use_shell = True
else:
    concat_args = False
    use_shell = False

def catch_errors(lines):
    for line in lines:
        if re.search('^Traceback', line):
            logging.error('Backtrace produced')

def Popen(*args, **kwargs):    
    kwargs['shell'] = use_shell
    if concat_args:
        args = (' '.join(args[0]),) + args[1:]
    try:
        return subprocess.Popen(*args, **kwargs)
    except:
        sys.stderr.write("ERROR: Cannot run command `%s'\n"%' '.join(args[0]))
        sys.stderr.write("ABORTING\n")
        sys.exit(1)

def call(command, cwd=None):
    logging.debug("Run: %s" % ' '.join(command))
    process = Popen(command, cwd=cwd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout_lines = [line.strip() for line in process.stdout.readlines()]
    catch_errors(stdout_lines)
    stderr_lines = [line.strip() for line in process.stderr.readlines()]
    catch_errors(stderr_lines)
    if stdout_lines or stderr_lines:
        logging.debug('\n'.join(stderr_lines))
        logging.debug('\n'.join(stdout_lines))
    return (stdout_lines, stderr_lines)

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

