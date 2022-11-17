import os
import xml.dom.minidom
import sys
import re
import random
import shutil
import hashlib
from xpd import templates
from xmos_logging import log_error, log_warning, log_info, log_debug
from xmos_subprocess import call_get_output, platform_is_windows

rst_title_regexp = r'[-=^~#.][-=^~#.]+'

rand = random.Random()

flat_projects = True

def replace_path_sep(path):
    if platform_is_windows():
        path = path.replace('\\','/')
    return path

def prompt(force, prompt, default):
    if force:
        x = 'y' if default else 'n'
    else:
        print("%s (y/n) [%s]? " % (prompt, ('y' if default else 'n')))
        x = input()

    if default:
        return x.upper() not in ['N', 'NO']
    else:
        return x.upper() not in ['Y', 'YES']

def file_changed(path):
    (folder, filename) = os.path.split(path)
    (stdout_lines, stderr_lines) = call_get_output(["git", "status", '--porcelain', filename], cwd=folder)
    if not stdout_lines and not stderr_lines:
        return False
    else:
        return True

def new_id(m):
     return "id = \"" + m.groups(0)[0] + "." + str(rand.randint(0,100000000)) + "\""

def getFirstChild(node,tagname):
    for child in node.childNodes:
        if hasattr(child,'tagName') and child.tagName == tagname:
            return child
    return None

def get_project_name(repo,path):
     if path == repo.path:
          return repo.name
     else:
          return "%s" % (os.path.basename(path))

def is_non_xmos_project(name, repo):
    if name in repo.non_xmos_projects:
        return True
    if re.match('^(host_|pc_|osx_|win_|linux_).*', name):
        return True
    return False

def find_all_subprojects(repo,exclude_apps=False):
     path = repo.path
     subs = set([])
     for x in os.listdir(path):
          if x == 'doc':
               continue
          if x in repo.exclude_dirs:
              continue
          if x in repo.docdirs:
              continue
          if x.startswith('__'):
               continue
          if exclude_apps and x.startswith('app_'):
               continue
          if repo.is_untracked(x):
              continue
          mkfile = os.path.join(path,x,'Makefile')
          modinfo = os.path.join(path,x,'module_build_info')
          if os.path.exists(mkfile) or os.path.exists(modinfo) or x == 'module_xcommon' or re.match('^module_.*',x) or is_non_xmos_project(x, repo):
               subs.add(x)
     return subs

def check_project(repo, force_creation=False):
     ok = True
     if flat_projects:
          for sub in find_all_subprojects(repo):
               proj_ok = _check_project(repo, path=os.path.join(repo.path,sub), force_creation=force_creation)
               ok = ok and proj_ok

          if os.path.exists(os.path.join(repo.path,'.project')):
               log_debug("Found top level .project, removing...")
               repo.git_remove(os.path.join(repo.path,'.project'))
               ok = False
          if os.path.exists(os.path.join(repo.path,'.cproject')):
               log_debug("Found top level .cproject, removing...")
               repo.git_remove(os.path.join(repo.path,'.cproject'))
               ok = False
     else:
          ok = _check_project(repo, force_creation=force_creation)
     return ok

def find_all_app_makefiles(path):
    makefiles = set()
    for x in os.listdir(path):
        if x[0:4] == 'app_' or x[0:5] == 'test_':
            mkfile = os.path.join(path,x,'Makefile')
            if os.path.isfile(mkfile):
                makefiles.add(mkfile)
    return makefiles


def parse_makefile(path):
    f = open(path)
    lines = f.readlines()
    f.close()
    vals = {}
    for line in lines:
        m = re.match('(\w*)\s*[\?]?=\s*(.*)',line)
        if m:
            vals[m.groups(0)[0]] = m.groups(1)[1]
    return vals

def get_configs(mkfile_path):
    folder = os.path.dirname(mkfile_path)
    mkfile_name = os.path.basename(mkfile_path)
    (stdout_lines, stderr_lines) = call_get_output(["xmake", "allconfigs", "-f", mkfile_name], cwd=folder)
    configs = set()
    if len(stdout_lines):
      configs = set(stdout_lines[0].strip().split(" "))
    else:
      configs = set(['Default'])
    return configs

def get_all_configs(makefiles):
    configs = set(['Default'])
    for mkfile in makefiles:
        mkfile_configs = get_configs(mkfile)
        configs = configs | mkfile_configs

    if 'Debug' in configs:
        configs.add('Release')
    return configs

def create_xproject_str(repo,is_documentation=False, is_hidden = False):
   xproject_str = '<?xml version="1.0" encoding="UTF-8"?>'
   xproject_str += '<xproject>'
   xproject_str += '<repository>%s</repository>'%repo.name
   if repo.partnumber:
        xproject_str += '<partnum>%s</partnum>'%repo.subpartnumber

   rel = repo.current_release()
   if rel:
        xproject_str += '<version>%s</version>'%str(rel.version)

   if is_documentation:
        xproject_str += '<documentation/>'

   if is_hidden:
        xproject_str += '<hidden/>'

   xproject_str += '</xproject>'
   return xproject_str

def create_xproject(repo, path):
   is_hidden = False
   if re.match('.*module_xcommon',path):
        is_hidden = True
   xproject_str = create_xproject_str(repo,is_hidden=is_hidden)
   f = open(os.path.join(path,'.xproject'), 'wb')
   f.write(xproject_str)
   f.close()

def create_doc_project(repo):
   dotproject_str = templates.documentation_dotproject
   dotproject_str = dotproject_str.replace('%PROJECT%',
                                           'Documentation [%s]' % repo.name)
   return (dotproject_str, create_xproject_str(repo,is_documentation=True))

def create_cproject(repo, path=None, name=None, configs=None, all_includes=[],
                    is_module=False):
   if is_non_xmos_project(name, repo):
       create_xproject(repo, path)
       return

   is_extra_project = (os.path.basename(path) in repo.extra_eclipse_projects)
   if path==None:
        path = repo.path
   if name==None:
        name = get_project_name(repo, path)
   if configs==None:
        if is_module or is_extra_project:
             configs = set(['Default'])
        elif path == repo.path:
             configs = get_all_configs(path)
        else:
             configs = get_configs(os.path.join(path,'Makefile'))
   cproject_path = os.path.join(path,'.cproject')
   seed = int(hashlib.md5(name).hexdigest(), 16)
   rand.seed(seed)
   if 'Default' in configs:
        base_config = ''
   elif 'Release' in configs:
        base_config = '_Release'
   elif len(configs) > 0:
        base_config = '_' + (list(configs)[0])
   else:
        base_config = ''

   includes = ['<listOptionValue builtIn="false" value=\'%s\' />\n'%x for x in sorted(all_includes)]
   includes = ''.join(includes)

   # On Windows need to write out paths with '/' instead of '\'
   includes = replace_path_sep(includes)

   config_str = ''
   for config in configs:
       config_id = str(rand.randint(1,100000000))
       lines = templates.cproject_configuration.split('\n')
       if config == 'Default':
           config_args = ''
           config_output_dir='bin'
       else:
           config_args = 'CONFIG=%s'%config
           config_output_dir='bin/%s'%config

       if is_module or is_extra_project:
            config_args += ' -f .makefile'

       for i in range(len(lines)):
           lines[i] = lines[i].replace('%PROJECT%',name)
           lines[i] = lines[i].replace('%CONFIG%',config)
           lines[i] = lines[i].replace('%CONFIG_OUTPUT_DIR%',config_output_dir)
           lines[i] = lines[i].replace('%CONFIG_ARGS%',config_args)
           lines[i] = lines[i].replace('%INCLUDES%',includes)
           lines[i] = re.sub(r'id\s*=\s*[\'"]([\w.]*)\.\d*[\'"]',new_id,lines[i])
           lines[i] = lines[i].replace('%CONFIG_ID%',config_id)

       config_str += '\n'.join(lines)

   lines = templates.cproject.split('\n')
   for i in range(len(lines)):
       lines[i] = lines[i].replace('%PROJECT%',name)
       lines[i] = re.sub(r'id\s*=\s*[\'"]([\w.]*)\.\d*[\'"]',new_id,lines[i])
       lines[i] = lines[i].replace('%CONFIGURATIONS%',config_str)

   f = open(os.path.join(path,'.cproject'), 'wb')
   f.write('\n'.join(lines))
   f.close()

   if is_module:
        f = open(os.path.join(path,'.makefile'), 'wb')
        f.write(templates.module_makefile)
        f.close()

   if is_extra_project:
        f = open(os.path.join(path,'.makefile'), 'wb')
        f.write(templates.extra_project_makefile)
        f.close()

   create_xproject(repo, path)

def valid_include_path(relpath):
     if re.match('^doc.*', relpath):
          return False

     if re.match('.*' + re.escape(os.path.sep) + 'doc$', relpath):
          return False

     if re.match('^__.*', relpath):
          return False

     if re.match('.*' + re.escape(os.path.sep) + '__.*', relpath):
          return False

     if re.match('(^|.*' + re.escape(os.path.sep) + ')_build.*', relpath):
          return False

     if re.search('(^|.*' + re.escape(os.path.sep) + ')\.build', relpath):
          return False

     if re.search('(^|.*' + re.escape(os.path.sep) + ')bin', relpath):
          return False

     return True


def check_makefile(mkfile_path, repo, all_configs):
    updates_required = False
    relpath = os.path.relpath(mkfile_path,repo.path)
    configs = get_configs(mkfile_path)
    f = open(mkfile_path)
    lines = f.readlines()
    f.close()
    found_xcommon =False
    for line in lines:
        if re.match('.*xcommon.*', line):
             found_xcommon = True
        if re.match('all:.*', line):
            log_warning("%s defines all target" % relpath)
            updates_required = True
        if re.match('clean:.*', line):
            log_warning("%s defines clean target" % relpath)
            updates_required = True

        if re.match('\s*USED_MODULES\s*=.*module_(\w*)\.\d', line):
            log_warning("%s has explicit module versions" % relpath)
            updates_required = True

        m = re.match('-?include(.*Makefile.common)', line)
        if m:
            include_path = m.groups(0)[0].strip()
            if include_path != \
               '$(XMOS_MAKE_PATH)/xcommon/module_xcommon/build/Makefile.common':
                log_warning("%s has incorrect xcommon include" % relpath)
                updates_required = True

    if not found_xcommon:
         log_debug("Doesn't look like an xcommon makefile ... leaving alone")
         updates_required = False

    return updates_required


include_section = """
#=============================================================================
# The following part of the Makefile includes the common build infrastructure
# for compiling XMOS applications. You should not need to edit below here.

XMOS_MAKE_PATH ?= ../..
include $(XMOS_MAKE_PATH)/xcommon/module_xcommon/build/Makefile.common
"""

def update_makefile(mkfile_path, all_configs):
    configs = get_configs(mkfile_path)
    f = open(mkfile_path)
    lines = f.readlines()
    f.close()
    found_xcommon = False
    for line in lines:
        if re.match('.*xcommon.*', line):
             found_xcommon = True
    if not found_xcommon:
         return

    in_config_branch = None
    newlines = []
    comments = []
    past_include = False
    for line in lines:
        skip_line = False
        m = re.match('\s*(XCC.*_FLAGS) (.*)', line)
        if in_config_branch and in_config_branch != '' and m:
            flags = m.groups(0)[0]
            rhs = m.groups(0)[1]
            line = '%s_%s %s\n' %(flags,in_config_branch,rhs)

        m = re.match('ifeq "\$\(CONFIG\)" "(\w*)"', line)
        if m:
            in_config_branch = m.groups(0)[0]
            skip_line = True

        if in_config_branch and re.match('.*endif', line):
            in_config_branch = None
            skip_line = True

        if in_config_branch and re.match('.*else', line):
            if in_config_branch == 'Debug':
                in_config_branch = 'Release'
            elif in_config_branch == 'Release':
                in_config_branch = 'Debug'
            else:
                in_config_branch = ''
            skip_line = True

        if re.match('-?include(.*)Makefile.common', line):
            past_include = True

        line = re.sub(r'module_(\w*)\.[\d|v]*',r'module_\1',line)

        if not skip_line and not past_include:
            if line[0] == '#' or line == '\n' or re.match('XMOS_MAKE_PATH.*', line):
                comments.append(line)
            else:
                newlines += comments
                comments = []
                newlines.append(line)

    if newlines[-1] != '\n':
        newlines.append('\n')

    if 'Default' in configs:
        base_config = ''
    elif 'Release' in configs:
        base_config = '_Release'
    elif len(configs) > 0:
         base_config = '_' + (list(configs)[0])
    else:
         base_config = ''

    f = open(mkfile_path, 'wb')
    f.write(''.join(newlines) + include_section)
    f.close()

def check_toplevel_makefile(repo, force_creation=False):
    log_debug("Checking toplevel Makefile")
    updates_required = False
    path = os.path.join(repo.path,'Makefile')

    try:
         f = open(path)
    except:
         updates_required = True
         log_debug("Toplevel Makefile does not exist")

    if not updates_required:
         lines = f.readlines()
         f.close()
         found_include = False
         for line in lines:
              if line == 'include $(XMOS_MAKE_PATH)/xcommon/module_xcommon/build/Makefile.toplevel\n':
                   found_include = True

         if not found_include:
              log_warning("Toplevel Makefile not standard")

    if updates_required:
        if prompt(force_creation, "There is a problem with the toplevel Makefile.\n" +
                                  "Do you want xpd to create a new one", True):
             f = open(os.path.join(repo.path,'Makefile'), 'w')
             f.write(templates.toplevel_makefile)
             f.close()
             if file_changed(path):
                 log_info("New toplevel Makefile created")

    return updates_required

def check_makefiles(repo, force_creation=False):
    updates_required = check_toplevel_makefile(repo, force_creation=force_creation)
    makefiles = find_all_app_makefiles(repo.path)
    all_configs = get_all_configs(makefiles)
    for mkfile in makefiles:
        log_debug("Checking %s" % os.path.relpath(mkfile, repo.path))
        if flat_projects:
             configs = get_all_configs(set([mkfile]))
        else:
             configs = all_configs
        dirname = os.path.dirname(os.path.relpath(mkfile, repo.path))
        updates_required |= check_makefile(mkfile, repo, configs)
    if updates_required:
        if prompt(force_creation, "Makefiles need updating. Do updates", True):
            for mkfile in makefiles:
                if flat_projects:
                       configs = get_all_configs(set([mkfile]))
                else:
                      configs = all_configs
                update_makefile(mkfile, configs)
                log_info("Updated %s" % os.path.relpath(mkfile, repo.path))

    return (not updates_required)

def write_changelog_title(repo, f):
    title = "%s Change Log" % repo.name 
    f.write(title + '\n')
    f.write(('=' * len(title)) + '\n\n')

def check_changelog(repo, force_creation=False):
    ok = True
    changelog_path = os.path.join(repo.path, 'CHANGELOG.rst')
    if not os.path.exists(changelog_path):
        log_warning("Cannot find CHANGELOG.rst")
        if prompt(force_creation, "Create template CHANGELOG.rst ", True):
            log_info("Adding template CHANGELOG.rst")
            f = open(changelog_path, 'wb')
            f.write(templates.changelog)
            f.close()
            repo.git_add('CHANGELOG.rst')
            ok = False

    else:
        f = open(changelog_path)
        lines = f.readlines()
        f.close()

        title_error = False
        replace_title = False
        n_blank_lines = 0
        for i, line in enumerate(lines):
            line = line.strip()

            # Ignore blank lines at the start of the file
            if not line:
                n_blank_lines += 1
                continue
                
            if line[0] == '<':
                log_error("CHANGELOG.rst is still empty template - please update it")
                sys.exit(1)

            if not re.search("change log", line, re.IGNORECASE):
                title_error = True

            # The title must have a section line after it
            if i < (len(lines) - 1):
                if re.match(rst_title_regexp, lines[i+1]):
                    replace_title = True
                    break

            # Otherwise it is an error
            title_error = True
            break

        if title_error:
            log_warning('Title section in %s CHANGELOG.rst not valid' % repo.name)
            ok = False
            if prompt(force_creation, "Add valid title section", True):
                f = open(changelog_path, 'wb')
                write_changelog_title(repo, f)

                if replace_title:
                    start_line = 2
                else:
                    start_line = 0

                for line in lines[start_line + n_blank_lines:]:
                    f.write(line)
                f.close()
                log_info("Updated %s" % changelog_path)

    return ok

def check_docdir(repo):
     pass

def patch_makefile(makefile_str):
    lines = makefile_str.split('\n')
    for line in lines:
        if re.match('.*Makefile.toplevel',line):
            return makefile_str
    
    new_lines = []
    found_common_include = False
    breakline = 0

    for line in lines:
        if re.match('# The following part of the', line) or re.match('XMOS_MAKE_PATH', line):
            found_common_include = True
            break
        new_lines.append(line)
        breakline += 1
     
    if not found_common_include:
        return makefile_str

    if re.match('#=============================================================================', new_lines[-1]):
        new_lines = new_lines[:-1]
    makefile_str = '\n'.join(new_lines)
    makefile_str += templates.makefile_include_str

    return makefile_str

