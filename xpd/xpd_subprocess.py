## Annoying OS incompatability, not sure why this is needed
import re
import platform
import subprocess
import sys

ostype = platform.system()

if not re.match('.*Darwin.*',ostype) and re.match('.*[W|w]in.*',ostype):
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
        return subprocess.Popen(*args,**kwargs)
    except:
        sys.stderr.write("ERROR: Cannot run command `%s'\n"%' '.join(args[0]))
        sys.stderr.write("ABORTING\n")
        sys.exit(1)

def call(*args, **kwargs):
    kwargs['shell'] = use_shell
    if concat_args:
        args = (' '.join(args[0]),) + args[1:]
    try:
        return subprocess.call(*args,**kwargs)
    except:
        sys.stderr.write("ERROR: Cannot run command `%s'\n"%' '.join(args[0]))
        sys.stderr.write("ABORTING\n")
        sys.exit(1)

