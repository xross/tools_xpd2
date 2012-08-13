# -*- mode: python -*-
import os
import re

cwd = os.getcwd()

a = Analysis([os.path.join(HOMEPATH,'support/_mountzlib.py'), os.path.join(HOMEPATH,'support/useUnicode.py'), 'scripts/xpd'],
             pathex=[cwd])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=os.path.join('dist', 'xpd.exe'),
          debug=False,
          strip=False,
          upx=True,
          console=1 )
