# -*- mode: python -*-
import os
import re

cwd = os.getcwd()

tools_xdoc_path = os.path.join(cwd,'..','tools_xdoc')

sys.path.insert(0,tools_xdoc_path)

a = Analysis([os.path.join(HOMEPATH,'support/_mountzlib.py'),
              os.path.join(HOMEPATH,'support/useUnicode.py'),
              'scripts/xpd',
              os.path.join(tools_xdoc_path, 'xdoc', 'xsphinx', 'conf.py'),
              os.path.join(tools_xdoc_path, 'xdoc', 'xsphinx', 'breathe', 'breathe', '__init__.py'),
              os.path.join(tools_xdoc_path,'doc_snippets','scripts', 'unweave.py'),
              '../infr_docs/xmossphinx/xmosconf.py',
              os.path.join(tools_xdoc_path, 'aafigure', '__init__.py'),
              os.path.join(tools_xdoc_path, 'reportlab', '__init__.py')],

             pathex=[cwd,
                     os.path.join(cwd,'xpd'),
                     os.path.join(cwd,'..','tools_python_hashlib','install','lib','python'),
                     os.path.join(cwd,'..','tools_python_hashlib','install','lib64','python'),
                     tools_xdoc_path,
                     os.path.join(cwd,'..','lib_cognidox'),
                     os.path.join(cwd,'..','lib_logging_py'),
                     os.path.join(cwd,'..','lib_subprocess_py'),
                     os.path.join(cwd,'..','lib_xmlobject_py'),
                     os.path.join(tools_xdoc_path,'xdoc'),
                     os.path.join(tools_xdoc_path,'xdoc','xsphinx'),
                     os.path.join(tools_xdoc_path,'xdoc','xsphinx','breathe'),
                     os.path.join(tools_xdoc_path,'doc_snippets','scripts'),
                     os.path.abspath(os.path.join(cwd,'..','infr_docs')),
                     os.path.abspath(os.path.join(cwd,'..','infr_docs','xmossphinx','builders'))],
             hiddenimports=['sphinx.builders.text','breathe','breathe.builder','breathe.finder',
                            'breathe.parser','breathe.parser.doxygen','breathe.parser.doxygen.index','breathe.parser.doxygen.compound',
                            'breathe.parser.doxygen.compoundsuper','xmosconf', 'unweave',
                            'aafigure','aafig','reportlab',
                            'reportlab.lib.colors', 'reportlab.graphics.shapes',
                            'reportlab.graphics.renderPDF','reportlab.pdfbase.pdfmetrics', 'reportlab.pdfbase.ttfonts',
                            'reportlab.pdfbase._can_cmap_data',
                            'reportlab.pdfbase._cidfontdata',
                            'reportlab.pdfbase.cidfonts',
                            'reportlab.pdfbase._fontdata_enc_macexpert',
                            'reportlab.pdfbase._fontdata_enc_macroman',
                            'reportlab.pdfbase._fontdata_enc_pdfdoc',
                            'reportlab.pdfbase._fontdata_enc_standard',
                            'reportlab.pdfbase._fontdata_enc_symbol',
                            'reportlab.pdfbase._fontdata_enc_winansi',
                            'reportlab.pdfbase._fontdata_enc_zapfdingbats',
                            'reportlab.pdfbase._fontdata',
                            'reportlab.pdfbase._fontdata_widths_courierboldoblique',
                            'reportlab.pdfbase._fontdata_widths_courierbold',
                            'reportlab.pdfbase._fontdata_widths_courieroblique',
                            'reportlab.pdfbase._fontdata_widths_courier',
                            'reportlab.pdfbase._fontdata_widths_helveticaboldoblique',
                            'reportlab.pdfbase._fontdata_widths_helveticabold',
                            'reportlab.pdfbase._fontdata_widths_helveticaoblique',
                            'reportlab.pdfbase._fontdata_widths_helvetica',
                            'reportlab.pdfbase._fontdata_widths_symbol',
                            'reportlab.pdfbase._fontdata_widths_timesbolditalic',
                            'reportlab.pdfbase._fontdata_widths_timesbold',
                            'reportlab.pdfbase._fontdata_widths_timesitalic',
                            'reportlab.pdfbase._fontdata_widths_timesroman',
                            'reportlab.pdfbase._fontdata_widths_zapfdingbats',
                            'reportlab.pdfbase.pdfdoc',
                            'reportlab.pdfbase.pdfform',
                            'reportlab.pdfbase.pdfmetrics',
                            'reportlab.pdfbase.pdfpattern',
                            'reportlab.pdfbase.pdfutils',
                            'reportlab.pdfbase.rl_codecs',
                            'reportlab.pdfbase.ttfonts'])


def get_files(src, dst):
    def walk(path, prefix):
        for f in os.listdir(path):
            if os.path.isdir(os.path.join(path,f)):
                for x in walk(os.path.join(path,f),os.path.join(prefix,f)):
                    yield x
            else:
                yield os.path.join(prefix, f)

    import re
    files = []
    for path in walk(src,''):
        if not re.match('.*pyc$',path):
            files.append(path)

    return [(os.path.normpath(os.path.join(dst,p)),os.path.abspath(os.path.join(src,p)),'DATA') for p in files]

data_files = ['xsphinx/Doxyfile','xsphinx/conf.py']

xmosroot = os.environ['XMOS_ROOT']

data_files_toc = [(p,os.path.join(xmosroot,'tools_xdoc','xdoc',p),'DATA') for p in data_files] + \
                 get_files('../tools_xdoc/xdoc/xsphinx/themes','xsphinx/themes') + \
                 get_files(os.path.join(xmosroot,'infr_docs','base'),'texinputs') + \
                 get_files(os.path.join(xmosroot,'infr_docs/xmossphinx/themes'),'infr_docs/xmossphinx/themes') + \
                 get_files('../tools_xdoc/xdoc/texinput','texinputs') + \
                 get_files('../tools_xdoc/texinputs','texinputs')

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('dist', 'xpd.exe'),
          debug=False,
          strip=None,
          upx=True,
          console=True)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               data_files_toc,
               strip=None,
               upx=True,
               name=os.path.join('dist', 'xpd'))

