## Annoying OS incompatability, not sure why this is needed
import re
import platform
import subprocess

use_shell = re.match('.*[W|w]in.*',platform.system())
def Popen(*args, **kwargs):
    kwargs['shell'] = use_shell
    return subprocess.Popen(*args,**kwargs)

def call(*args, **kwargs):
    kwargs['shell'] = use_shell
    return subprocess.call(*args,**kwargs)
