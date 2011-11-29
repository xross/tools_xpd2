## Annoying OS incompatability, not sure why this is needed
import re
import platform
import subprocess

ostype = platform.system()

if not re.match('.*Darwin.*',ostype) and re.match('.*[W|w]in.*',ostype):
    use_shell = True
else:
    use_shell = False

def Popen(*args, **kwargs):
    kwargs['shell'] = use_shell
    return subprocess.Popen(*args,**kwargs)

def call(*args, **kwargs):
    kwargs['shell'] = use_shell
    return subprocess.call(*args,**kwargs)
