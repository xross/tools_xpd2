## Annoying OS incompatability, not sure why this is needed
import re
import platform
import subprocess

if re.match('.*[W|w]in.*',platform.system()):
    use_shell = True
    join_args = False
elif re.match('.*Darwin.*',platform.system()):
    use_shell = True
    join_args = True
else:
    use_shell = False
    join_args = False

def Popen(*args, **kwargs):
    if join_args:
        args = list(args)
        args[0] = [' '.join(args[0])]

    kwargs['shell'] = use_shell
    return subprocess.Popen(*args,**kwargs)

def call(*args, **kwargs):
    if join_args:
        args = list(args)
        args[0] = [' '.join(args[0])]

    kwargs['shell'] = use_shell
    return subprocess.call(*args,**kwargs)
