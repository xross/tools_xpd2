#! /usr/bin/env python

from github import Github
import pexpect
import logging
import os
import platform
import re
import subprocess
import sys
import tempfile
import time

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
        log_error("Cannot run command `%s'\n"%' '.join(args[0]), exc_info=True)
        sys.exit(1)

def call(command, cwd=None):
    """ Run the command requested and return the stdout/stderr expected
    """
    if cwd:
        log_debug("Run: '%s' in %s" % (' '.join(command), cwd))
    else:
        log_debug("Run: '%s' in %s" % (' '.join(command), os.getcwd()))

    # Create temporary files to pass stdout and stderr to since on Windows the
    # less/more-like behaviour waits for a keypress if it goes to stdout.
    out = tempfile.TemporaryFile()
    err = tempfile.TemporaryFile()
    process = Popen(command, cwd=cwd, stdout=out, stderr=err)
    process.wait()
    out.seek(0)
    err.seek(0)

    stdout_lines = [line.strip() for line in out.readlines()]
    catch_errors(stdout_lines)
    stderr_lines = [line.strip() for line in err.readlines()]
    catch_errors(stderr_lines)
    for line in stdout_lines + stderr_lines:
        log_debug(line)
    return (stdout_lines, stderr_lines)


class Expect(object):
    """ Container for a set of expected output and their responses.
        The default timeout version is the default for the process
        as defined at that spawn.
    """
    def __init__(self, values=None, responses=None, timeout=-1):
        if values and responses:
            assert len(values) == len(responses)

        self.values = values
        self.responses = responses
        self.timeout = timeout


def interact(command, expected, cwd=None, early_out=False, timeout=30):
    """ Interact with a process given a list of expected output and responses.
        Also keeps track of all output seen to check for errors at the end.

        Each expected output is a set of options that are looked for in parallel.
        The responses should be a list of the same length as the expected outputs.

        Returns the final index in the list of expected output and the option from
        that entry that was matched.
    """
    if cwd:
        os.chdir(cwd)
    log_debug("Interact: '%s' in %s" % (' '.join(command), os.getcwd()))
    process = pexpect.spawn(' '.join(command), timeout=timeout)

    all_output = ''
    last_index = 0
    last_option = 0
    for expect in expected:
        if expect.values:
            value = '(' + '|'.join(expect.values) + ')'
            log_debug("Interact: expect '%s'" % value)
            try:
                process.expect(value, timeout=expect.timeout)
                all_output += process.before
                all_output += process.after
            except pexpect.EOF:
                if not early_out:
                    log_error("Interact: unexpected EOF")
                process.close()
                break
            except pexpect.TIMEOUT:
                log_error("Interact: TIMEDOUT")
                if process.before:
                    all_output += process.before
                process.close()
                break

        # Find the index that matched and send the appropriate response. Default to index 0
        # if nothing was expected
        last_option = 0
        if expect.values:
            for (i, value) in enumerate(expect.values):
                if re.search(value, process.after):
                    last_option = i
                    break
                
        # Want to be able to send blank lines (use default value) hence not None check
        if expect.responses[last_option] is not None:
            log_debug("Interact: send '%s'" % expect.responses[last_option])
            process.sendline(expect.responses[last_option])

        last_index += 1

    if process.isalive():
        # If the process is still alive wait for it to complete
        try:
            process.expect(pexpect.EOF)
        except pexpect.TIMEOUT:
            log_error("Interact: TIMEDOUT")
            process.close()

        if process.before:
            all_output += process.before

        time.sleep(0.1) # Required according to pexpect documentation to guarantee process has been updated
        assert not process.isalive()

    catch_errors(all_output)
    for line in all_output.split('\n'):
        log_debug(line.rstrip())

    return (last_index, last_option)

def catch_errors(lines):
    for line in lines:
        if re.search('^Traceback', line):
            log_error('backtrace produced')
        if re.search('^fatal:', line):
            log_error('git error detected')
        if re.search('^ERROR:', line):
            log_error('xpd error detected (%s)' % line.rstrip())
        if re.search('\(ERROR/', line):
            log_error('document error detected')

def check_exists(files):
    for f in files:
        if not os.path.exists(f):
            log_error("Missing %s" % f)
        else:
            log_debug("Found required file %s" % f)

def get_apps_from_github(tests_folder):
    """ Clone all the public repos from github. If the folder already exists then simply
        update it.
    """
    github = Github()
    org = github.get_organization('Xcore')
    repos = org.get_repos('public')
    for repo in repos:
        os.chdir(tests_folder)

        test_name = 'test_' + repo.name
        test_folder = os.path.join(test_name, repo.name)

        if os.path.exists(test_folder):
            log_info("Updating %s" % repo.name)
            call(['git', 'pull'], cwd=os.path.join(tests_folder, test_folder))

        else:
            log_info("Cloning %s" % repo.name)
            if not os.path.exists(test_name):
                os.mkdir(test_name)
            call(['git', 'clone', repo.clone_url], cwd=os.path.join(tests_folder, test_name))

def get_parent(folder):
    return os.path.sep.join(os.path.split(folder)[:-1])

def get_xpd_contents(folder):
    xpd_contents = []
    if os.path.exists(os.path.join(folder, 'xpd.xml')):
        with open(os.path.join(folder, 'xpd.xml')) as xpd:
            xpd_contents = xpd.readlines()
    return xpd_contents

def git_has_origin(folder):
    (stdout_lines, stderr_lines) = call(['git', 'branch', '-a'], cwd=folder)
    for line in stdout_lines + stderr_lines:
        if re.search("origin/master", line):
            return True
    return False

counts = {
    'errors': 0,
    'warnings' : 0
}

def log_error(message):
    logging.error(message)
    counts['errors'] += 1

def log_warning(message):
    logging.warning(message)
    counts['warnings'] += 1

def log_info(message):
    logging.info(message)

def log_debug(message):
    logging.debug(message)

def print_summary():
    print "\nTotal warnings: %d, errors %d" % (counts['warnings'], counts['errors'])

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

