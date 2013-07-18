import os
import xml.dom.minidom
import sys
import re
import subprocess
import random
import shutil
import hashlib
from xpd import templates
from xpd.xpd_logging import *

rst_title_regexp = r'[-=^~.][-=^~.]+'

rand = random.Random()

flat_projects = True

def prompt(force, prompt, default):
    if force:
        x = 'y' if default else 'n'
    else:
        print "%s (y/n) [%s]? " % ('y' if default else 'n')
        x = raw_input()

    if default:
        return x.upper() not in ['N', 'NO']
    else:
        return x.upper() not in ['Y', 'YES']

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

def _check_project(repo, path=None, force_creation=False):
    if not path:
        path = repo.path

    name = get_project_name(repo, path)
    log_debug("%s: checking .project file" % name)
    project_ok = True
    project_path = os.path.join(path, '.project')
    if not os.path.exists(project_path):
        log_warning("%s: .project file missing" % name)
        project_ok = False

    else:
        try:
            dom = xml.dom.minidom.parse(project_path)
            root = getFirstChild(dom, 'projectDescription')
            names = [x.toxml() for x in dom.getElementsByTagName('name')]
        except:
            log_warning("%s: .project file is invalid" % name)
            project_ok = False
            root = None
            names = []

        if not root:
            log_warning("%s: .project file is invalid" % name)
            project_ok = False

        if not '<name>com.xmos.cdt.core.ModulePathBuilder</name>' in names:
             log_warning("%s: .project file is invalid (no module path builder)" % name)
             project_ok = False

        if not '<name>com.xmos.cdt.core.IncludePathBuilder</name>' in names:
             log_warning("%s: .project file is invalid (no module path builder)" % name)
             project_ok = False

        if project_ok:
            name_node = getFirstChild(root, 'name')

            try:
                valid_name = (name_node.childNodes[0].wholeText == name)
            except:
                valid_name = False

            if not valid_name:
                log_warning("%s: eclipse project name is invalid" % name)
                project_ok = False

            projects = getFirstChild(root, 'projects')
            if projects and getFirstChild(projects, 'project'):
                log_warning("%s: eclipse project has related projects in it (probably a bad idea)" % name)
                project_ok = False

    if force_creation or not project_ok:
        if prompt(force_creation, "There is a problem with the eclipse .project file.\n" +
                                   "Do you want xpd to create a new one", True):
            project_lines = templates.dotproject.split('\n')
            f = open(os.path.join(path,'.project'), 'wb')
            for line in project_lines:
                line = line.replace('%PROJECT%', name)
                f.write(line+"\n")
            f.close()
            log_info("New .project created in %s" % name)
            project_ok = True

    repo.git_add(project_path)

    return project_ok

def find_all_subprojects(repo,exclude_apps=False):
     path = repo.path
     subs = set([])
     for x in os.listdir(path):
          if x == 'doc':
               continue
          if x.startswith('__'):
               continue
          if exclude_apps and x.startswith('app_'):
               continue
          mkfile = os.path.join(path,x,'Makefile')
          modinfo = os.path.join(path,x,'module_build_info')
          if os.path.exists(mkfile) or os.path.exists(modinfo) or x == 'module_xcommon' or (x in repo.extra_eclipse_projects) or re.match('^module_.*',x):
               subs.add(x)
     return subs

def get_project_immediate_deps(repo, project):
     mkfile = os.path.join(repo.path,project,'Makefile')
     modinfo = os.path.join(repo.path,project,'module_build_info')
     deps = []
     if os.path.exists(modinfo):
          for line in open(modinfo).readlines():
               m = re.match('.*DEPENDENT_MODULES\s*=\s*(.*)',line)
               if m:
                    deps += [x.strip() for x in m.groups(0)[0].split(' ')]

     if os.path.exists(mkfile):
          for line in open(mkfile).readlines():
               m = re.match('.*USED_MODULES\s*=\s*(.*)',line)
               if m:
                    deps += [x.strip() for x in m.groups(0)[0].split(' ')]

     return deps

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
    f = open(mkfile_path)
    lines = f.readlines()
    f.close()
    configs = set()
    flag_types = set()
    in_config_branch = None
    for line in lines:
        m = re.match('\s*XCC(.*)_FLAGS(\w*) .*',line)
        if m:
            flag_type = m.groups(0)[0]
            config = m.groups(0)[1]
            flag_types.add(flag_type)

            if config == '':
                if in_config_branch:
                    config = in_config_branch
                else:
                    config = 'Default'
            else:
                config = config[1:]
            configs.add(config)
        m = re.match('\s*INCLUDE_ONLY_IN_(\w*) .*',line)
        if m:
            config = m.groups(0)[0]
            configs.add(config)

        m = re.match('ifeq "\$\(CONFIG\)" "(\w*)"',line)
        if m:
            in_config_branch = m.groups(0)[0]

        if in_config_branch and re.match('.*endif',line):
            in_config_branch = None

        if in_config_branch and re.match('.*else',line):
            if in_config_branch == 'Debug':
                in_config_branch = 'Release'
            elif in_config_branch == 'Release':
                in_config_branch = 'Debug'
            else:
                in_config_branch = ''

    return flag_types, configs

def get_all_configs(makefiles):
    configs = set(['Default'])
    for mkfile in makefiles:
        (_, mkfile_configs) = get_configs(mkfile)
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

   if sys.platform.startswith('win'):
       # On Windows need to write out paths with '/' instead of '\'
       includes = includes.replace('\\','/')

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

def remove_repo_from_include(include):
     m = re.match('[^/]*/(.*)',include)
     if m:
          return m.groups(0)[0]
     else:
          return include

def valid_include_path(relpath):
     if re.match('^doc.*', relpath):
          return False

     if re.match('.*/doc$', relpath):
          return False

     if re.match('^__.*', relpath):
          return False

     if re.match('.*/__.*', relpath):
          return False

     if re.match('(^|.*/)_build.*', relpath):
          return False

     if re.search('(^|.*/)\.build', relpath):
          return False

     if re.search('(^|.*/)bin', relpath):
          return False

     return True

def _check_cproject(repo, makefiles, project_deps, path=None, force_creation=False):
    if not path:
         path = repo.path
         configs = get_all_configs(makefiles)
    elif os.path.exists(os.path.join(path,'Makefile')):
         _, configs = get_configs(os.path.join(path,'Makefile'))
    else:
         configs = ['Default']
    name = get_project_name(repo,path)
    print "Checking .cproject file [%s]" % os.path.basename(path)
    print "Using configs: %s" % ', '.join(configs)
    print 'Finding include directories'

    all_includes = set([os.path.basename(path)])
    for root, dirs, files in os.walk(path):
         for d in dirs:
              relpath = os.path.join(root,d)[len(path)+1:]
              if valid_include_path(relpath):
                   all_includes.add(os.path.join(os.path.basename(path),relpath))

    (_,deps) = project_deps[os.path.basename(path)]
    for dep in deps:
         if not dep in project_deps:
              log_error("%s: cannot find %s" % (name, dep))
              sys.exit(1)
         dep_repo = project_deps[dep][0]
         dep_path = os.path.join(dep_repo.path, dep)
         all_includes.add(dep)
         for root, dirs, files in os.walk(dep_path):
              for d in dirs:
                   relpath = os.path.join(root,d)[len(dep_path)+1:]
                   if valid_include_path(relpath):
                        all_includes.add(os.path.join(dep,relpath))

    if makefiles != set():
         is_module = False
    else:
         is_module = True

    all_includes = ['&quot;${workspace_loc:/%s}&quot;' % i \
                         for i in all_includes if i != '']

#    sys_includes = ['&quot;${XMOS_DOC_PATH}/../target/include&quot;']
#                    '&quot;${XMOS_TOOL_PATH}/target/include&quot;']
    sys_includes = []

    log_debug("%s: checking .cproject file" % name)
    cproject_ok = True
    cproject_path = os.path.join(path,'.cproject')
    if not os.path.exists(cproject_path):
        log_warning("%s: .cproject file missing" % name)
        cproject_ok = False

    else:
        f = open(cproject_path)
        lines = f.readlines()
        f.close()
        found_configs = set()
        unfound_includes = [x for x in all_includes]
        for line in lines:
            m = re.match(r'\s*\<configuration.*name\s*=\s*"([^"]*)".*', line)
            if m:
                found_configs.add(m.groups(0)[0])

            m = re.match(r'\s*<listOptionValue.*value\s*=\s*["\']([^"\']*)["\']', line)
            if m:
                try:
                    unfound_includes.remove(m.groups(0)[0])
                except:
                    pass
                try:
                    sys_includes.remove(m.groups(0)[0])
                except:
                    pass

        if unfound_includes != [] or sys_includes != []:
            log_warning("%s: .cproject does not cover all include paths" % name)
            cproject_ok = False

        if found_configs != configs:
            log_warning("%s: .cproject does not handle correct build configurations (handles %s)" % (name, ', '.join(found_configs)))
            cproject_ok = False

    if force_creation or not cproject_ok:
        if prompt(force_creation, "There is a problem with the eclipse .cproject file.\n" + 
                                  "Do you want xpd to create a new one", True):
            create_cproject(repo, path, name, configs, all_includes, is_module=is_module)
            log_info("New .cproject created in %s" % name)

    repo.git_add(cproject_path)
    repo.git_add(cproject_path.replace('.cproject','.xproject'))
    dotmakefile_path = cproject_path.replace('.cproject','.makefile')
    if os.path.exists(dotmakefile_path):
         repo.git_add(dotmakefile_path)

    return cproject_ok

def check_cproject(repo, force_creation=False, exclude_apps=False):
    ok = True
    project_deps = repo.get_project_deps()
    if flat_projects:
         for sub in find_all_subprojects(repo,exclude_apps):
              mkfile = os.path.join(repo.path,sub,'Makefile')
              makefiles = set([])
              if os.path.exists(mkfile) and not sub in repo.exports:
                   makefiles.add(mkfile)
              proj_ok = _check_cproject(repo, makefiles, project_deps, path=os.path.join(repo.path,sub),
                              force_creation=force_creation)
              ok = ok and proj_ok
    else:
         makefiles = find_all_app_makefiles(repo.path)
         ok = _check_cproject(repo, makefiles, project_deps,
                              force_creation=force_creation)
    return ok

def check_makefile(mkfile_path, repo, all_configs):
    updates_required = False
    relpath = os.path.relpath(mkfile_path,repo.path)
    flag_types, configs = get_configs(mkfile_path)
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

        m = re.match('-?include(.*)', line)
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
    flag_types, configs = get_configs(mkfile_path)
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

        if re.match('-?include.*',line):
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
             f = open(os.path.join(repo.path,'Makefile'), 'wb')
             f.write(templates.toplevel_makefile)
             f.close()
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
                if re.match(rst_title_regexp,lines[i+1]):
                    replace_title = True
                    break

            # Otherwise it is an error
            title_error = True
            break

        if title_error:
            log_warning('Title section in %s CHANGELOG.rst not valid' % repo.name)
            ok = False
            if prompt(force_creation, "Add valid title section", True):
                title = "%s Change Log" % repo.name 
                f = open(changelog_path, 'wb')
                f.write(title + '\n')
                f.write(('=' * len(title)) + '\n')

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
     for line in lines:
          if re.match('# The following part of the', line) or \
             re.match('XMOS_MAKE_PATH', line):
               found_common_include = True
               break
          new_lines.append(line)
     if not found_common_include:
          return makefile_str
     makefile_str = '\n'.join(new_lines)
     makefile_str += templates.makefile_include_str
     return makefile_str

