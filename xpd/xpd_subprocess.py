## Annoying OS incompatability, not sure why this is needed
import platform
import re
import subprocess
import sys
import StringIO
import tempfile
import traceback

from xpd.xpd_logging import *

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
        log_debug("Run: %s" % ' '.join(args[0]))
        return subprocess.Popen(*args, **kwargs)
    except:
        log_error("Cannot run command `%s'\n" % ' '.join(args[0]), exc_info=True)
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
            log_debug("     " + line.rstrip())
        
    else:
        process = Popen(*args, **kwargs)
        retval = process.wait()

    return retval

def call_get_output(*args, **kwargs):
    """ Create temporary files to pass stdout and stderr to since on Windows the
        less/more-like behaviour waits for a keypress if it goes to stdout.
    """
    out = tempfile.TemporaryFile()
    err = tempfile.TemporaryFile()
    kwargs['stdout'] = out
    kwargs['stderr'] = err
    process = Popen(*args, **kwargs)
    process.wait()

    out.seek(0)
    stdout_lines = out.readlines()
    out.close()

    err.seek(0)
    stderr_lines = err.readlines()
    err.close()

    return (stdout_lines, stderr_lines)

