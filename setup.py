#!/usr/bin/env python

from distutils.core import setup

setup(name='xpkg',
      version='0.1',
      description='XMOS packaging utitlity',
      author='Dave Lacey',
      author_email='david.lacey@xmos.com',
      url='http://github.com/xcore/tool_xpkg',
      packages=['xpkg'],
      scripts=['scripts/xpkg']
     )
