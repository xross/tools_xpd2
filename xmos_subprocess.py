## Annoying OS incompatability, not sure why this is needed
import platform
import re
import subprocess
import sys
import tempfile

from xmos_logging import log_error, log_warning, log_info, log_debug

def platform_is_windows():
    ostype = platform.system()
    if not re.match('.*Darwin.*', ostype) and re.match('.*[W|w]in.*', ostype):
        return True
    else:
        return False

def platform_is_osx():
    ostype = platform.system()
    if re.match('.*Darwin.*', ostype):
        return True
    else:
        return False

if platform_is_windows():
    concat_args = True
    use_shell = True
else:
    concat_args = False
    use_shell = False

def quote_string(s):
    """ For Windows need to put quotes around arguments with spaces in them
    """
    if re.search('\s', s):
        return '"%s"' % s
    else:
        return s

def Popen(*args, **kwargs):
    ignore_exceptions = kwargs.pop('ignore_exceptions', False)
    kwargs['shell'] = use_shell
    if concat_args:
        args = (' '.join([quote_string(arg) for arg in args[0]]),) + args[1:]
        cmd = args[0]
    else:
        cmd = ' '.join(args[0])

    try:
        log_debug("Run '%s' in %s" % (cmd, kwargs.get('cwd', '.')))
        return subprocess.Popen(*args, **kwargs)
    except Exception as e:
        if ignore_exceptions:
            raise e
        log_error("Cannot run command `%s'\n" % cmd, exc_info=True)
        sys.exit(1)

def call(*args, **kwargs):
    """ If silent, then create temporary files to pass stdout and stderr to since
        on Windows the less/more-like behaviour waits for a keypress if it goes to stdout.
    """
    silent = kwargs.pop('silent', False)
    retval = 0
    if silent:
        out = tempfile.TemporaryFile()
        kwargs['stdout'] = out
        kwargs['stderr'] = subprocess.STDOUT
        process = Popen(*args, **kwargs)
        retval = process.wait()

        out.seek(0)
        for line in out.readlines():
            log_debug('     ' + line.rstrip())

    else:
        process = Popen(*args, **kwargs)
        retval = process.wait()

    return retval

def call_get_output(*args, **kwargs):
    """ Create temporary files to pass stdout and stderr to since on Windows the
        less/more-like behaviour waits for a keypress if it goes to stdout.
    """
    merge = kwargs.pop('merge_out_and_err', False)

    out = tempfile.TemporaryFile()
    kwargs['stdout'] = out

    if merge:
        kwargs['stderr'] = subprocess.STDOUT
    else:
        err = tempfile.TemporaryFile()
        kwargs['stderr'] = err

    process = Popen(*args, **kwargs)
    process.wait()

    out.seek(0)
    stdout_lines = out.readlines()
    out.close()

    for line in stdout_lines:
        log_debug('     ' + line.rstrip())

    if not merge:
        err.seek(0)
        stderr_lines = err.readlines()
        err.close()

        for line in stderr_lines:
            log_debug('     err:' + line.rstrip())

    if merge:
        return stdout_lines
    else:
        return (stdout_lines, stderr_lines)
