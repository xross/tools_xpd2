#!/usr/bin/env python

from distutils.core import setup

setup(name='xpd',
      version='0.1',
      description='XMOS packaging utitlity',
      author='Dave Lacey',
      author_email='david.lacey@xmos.com',
      url='http://github.com/xcore/tool_xpd',
      packages=['xpd','xpd.ntlm'],
      scripts=['scripts/xpd']
     )
