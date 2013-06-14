#! /usr/bin/env python

import os
import subprocess
import platform
import re

ostype = platform.system()

if not re.match('.*Darwin.*', ostype) and re.match('.*[W|w]in.*', ostype):
    concat_args = True
    use_shell = True
else:
    concat_args = False
    use_shell = False

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

def call(*args, **kwargs):
    process = Popen(*args, **kwargs)
    return process.wait()

def run_get_stdout(command, cwd=None):
    process = Popen(command, cwd=cwd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    lines = process.stdout.readlines()
    return lines

def clean_repo(folder):
    """ Put the repository back into a known clean state
    """
    print "Cleaning %s" % folder
    os.chdir(folder)
    call(["git", "clean", "-xfdq"])
    call(["git", "reset", "HEAD"])
    call(["git", "checkout", "master"])

def test_pass(testname):
    print "PASS: %s" % testname

def test_fail(testname, reason):
    print "FAIL: %s: %s" % (testname, reason)

def test_xpd_version(top, folder):
    # Strip off the common bit of the path
    testname = folder[len(top):] + "_version"

    print "Running test_xpd_version %s" % testname

    clean_repo(folder)
    call(["xpd", "getdeps"])

    versions = run_get_stdout(["xpd", "list"], cwd=folder)
    if not versions:
        test_fail(folder, "No versions")
        return

    print "Checkout latest version '%s'" % versions[-1]
    call(["xpd", "checkout", versions[-1]])

    test_pass(testname)

def test_folder(top, folder):
    if os.path.isfile(os.path.join(folder, "xpd.xml")):
        test_xpd_version(top, folder)
        #test_xpd_latest(folder)
    else:
        for f in os.listdir(folder):
            if os.path.isdir(os.path.join(folder, f)):
                test_folder(top, os.path.join(folder, f))

if __name__ == "__main__":
    cwd = os.getcwd()
    test_folder(cwd, cwd)

