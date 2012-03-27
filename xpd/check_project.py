import os
import xml.dom.minidom
import sys
import re
import subprocess
import random
import shutil
from xpd.xpd_subprocess import call, Popen
from xpd import templates

rand = random.Random()

flat_projects = True

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

def _check_project(repo,path=None, force_creation=False):
    print "Checking .project file [%s]"%os.path.basename(path)
    if not path:
         path = repo.path
    name = get_project_name(repo,path)
    project_ok = True
    project_path = os.path.join(path,'.project')
    if not os.path.exists(project_path):
        print ".project file missing"
        project_ok = False

    else:
        try:
            dom = xml.dom.minidom.parse(project_path)
        except:
            print ".project file is invalid"
            project_ok = False

        root = getFirstChild(dom, 'projectDescription')

        names = [x.toxml() for x in dom.getElementsByTagName('name')]

        if not root:
            print ".project file is invalid"
            project_ok = False

        if not '<name>com.xmos.cdt.core.ModulePathBuilder</name>' in names:
             print ".project file is invalid (no module path builder)"
             project_ok = False

        if project_ok:


            name_node = getFirstChild(root, 'name')

            try:
                valid_name = (name_node.childNodes[0].wholeText == name)
            except:
                valid_name = False

            if not valid_name:
                print "Eclipse project name is invalid"
                project_ok = False

            projects = getFirstChild(root, 'projects')
            if projects and getFirstChild(projects, 'project'):
                print "Eclipse project has related projects in it (probably a bad idea)"
                project_ok = False

    if force_creation or not project_ok:
        if force_creation:
             x = 'y'
             sys.stdout.write("Creating new .project file\n")
        else:
             sys.stdout.write("There is a problem with the eclipse .project file.\n")
             sys.stdout.write("Do you want xpd to create a new one (Y/n)?")
             x = raw_input()
        if not x in ['n','N','No','NO','no']:
            project_lines = templates.dotproject.split('\n')
            f = open(os.path.join(path,'.project'),'w')
            for line in project_lines:
                line = line.replace('%PROJECT%',name)
                f.write(line)
            f.close()
            print "New .project created"
            project_ok = True

    return project_ok


def find_all_subprojects(repo):
     path = repo.path
     subs = set([])
     for x in os.listdir(path):
          if x == 'doc':
               continue
          mkfile = os.path.join(path,x,'Makefile')
          modinfo = os.path.join(path,x,'module_build_info')
          if os.path.exists(mkfile) or os.path.exists(modinfo) or x == 'module_xcommon' or (x in repo.extra_eclipse_projects) or re.match('^module_.*',x):
               subs.add(x)
     return subs

def check_project(repo, force_creation=False):
     print force_creation
     if flat_projects:
          for sub in find_all_subprojects(repo):
               _check_project(repo, path=os.path.join(repo.path,sub), force_creation=force_creation)
     else:
          _check_project(repo, force_creation=force_creation)


def find_all_app_makefiles(path):
    makefiles = set()
    for x in os.listdir(path):
        if x[0:4] == 'app_' or x[0:4] == 'test_':
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
   f = open(os.path.join(path,'.xproject'),'w')
   f.write(xproject_str)
   f.close()

def create_doc_project(repo):
   dotproject_str = templates.documentation_dotproject
   dotproject_str = dotproject_str.replace('%PROJECT%',
                                           'Documentation [%s]' % repo.name)
   return (dotproject_str, create_xproject_str(repo,is_documentation=True))

def create_cproject(repo, path=None, name=None, configs=None, all_includes=[],
                    is_module=False):
   if path==None:
        path = repo.path
   if name==None:
        name = get_project_name(repo, path)
   if configs==None:
        if path == repo.path:
             configs = get_all_configs(path)
        else:
             configs = get_configs(os.path.join(path,'Makefile'))
   cproject_path = os.path.join(path,'.cproject')
   if 'Default' in configs:
        base_config = ''
   elif 'Release' in configs:
        base_config = '_Release'
   elif len(configs) > 0:
        base_config = '_' + (list(configs)[0])
   else:
        base_config = ''

   includes = ['<listOptionValue builtIn="false" value=\'%s\' />\n'%x for x in all_includes]
   includes = ''.join(includes)
   is_extra_project = (os.path.basename(path) in repo.extra_eclipse_projects)
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

   f = open(os.path.join(path,'.cproject'),'w')
   f.write('\n'.join(lines))
   f.close()

   if is_module:
        f = open(os.path.join(path,'.makefile'),'w')
        f.write(templates.module_makefile)
        f.close()

   if is_extra_project:
        f = open(os.path.join(path,'.makefile'),'w')
        f.write(templates.extra_project_makefile)
        f.close()


   create_xproject(repo, path)


def remove_repo_from_include(include):
     m = re.match('[^/]*/(.*)',include)
     if m:
          return m.groups(0)[0]
     else:
          return include

def _check_cproject(repo,makefiles,path=None, force_creation=False):
    if not path:
         path = repo.path
    name = get_project_name(repo,path)
    print "Checking .cproject file [%s]" % os.path.basename(path)
    configs = get_all_configs(makefiles)
    if 'Debug' in configs and 'Release' in configs:
         configs.remove('Default')
    print "Using configs: %s" % ', '.join(configs)
    if makefiles != set():
         is_module = False
         sys.stdout.write('Finding include directories')
         sys.stdout.flush()
         all_includes = set()
         for mkfile in makefiles:
              sys.stdout.write('.')
              sys.stdout.flush()
              try:
                   process = Popen(["xmake","list_includes"],
                                   cwd=os.path.dirname(mkfile),
                                   stdout=subprocess.PIPE)
              except:
                   sys.stderr.write("ERROR: Cannot find xmake\n")
                   exit(1)

              lines = process.stdout.readlines()
              includes = ''
              for i in range(len(lines)-1):
                   if lines[i] == '**-includes-**\n':
                        includes = lines[i+1].strip()
                        break
              includes = includes.split(' ')
              all_includes = all_includes | set(includes)
              sys.stdout.write('\n')
    else:
         is_module = True
         all_includes = set()
         pass


    if flat_projects:
         all_includes = [remove_repo_from_include(x) for x in all_includes]

    all_includes = ['&quot;${workspace_loc:/%s}&quot;'%i \
                         for i in all_includes if i != '']

#    sys_includes = ['&quot;${XMOS_DOC_PATH}/../target/include&quot;']
#                    '&quot;${XMOS_TOOL_PATH}/target/include&quot;']
    sys_includes = []

    print "Checking .cproject file"
    cproject_ok = True
    cproject_path = os.path.join(path,'.cproject')
    if not os.path.exists(cproject_path):
        print ".cproject file missing"
        cproject_ok = False

    else:
        f = open(cproject_path)
        lines = f.readlines()
        f.close()
        found_configs = set()
        unfound_includes = [x for x in all_includes]
        for line in lines:
            m = re.match(r'\s*\<configuration.*name\s*=\s*"([^"]*)".*',line)
            if m:
                found_configs.add(m.groups(0)[0])

            m = re.match(r'\s*<listOptionValue.*value\s*=\s*["\']([^"\']*)["\']',line)
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
            print ".cproject does not cover all include paths"
            cproject_ok = False

        if found_configs != configs:
            print ".cproject does not handle correct build configurations"
            cproject_ok = False

    if force_creation or not cproject_ok:
        if force_creation:
             x = 'y'
             sys.stdout.write("Creating new .cproject file\n")
        else:
             sys.stdout.write("There is a problem with the eclipse .cproject file.\n")
             sys.stdout.write("Do you want xpd to create a new one (Y/n)?")
             x = raw_input()
        if not x in ['n','N','No','NO','no']:
             create_cproject(repo, path, name, configs, all_includes,is_module=is_module)
             print "New .cproject created."

    return cproject_ok

def check_cproject(repo,force_creation=False):
     if flat_projects:
          for sub in find_all_subprojects(repo):
               mkfile = os.path.join(repo.path,sub,'Makefile')
               makefiles = set([])
               if os.path.exists(mkfile):
                    makefiles.add(mkfile)
               _check_cproject(repo, makefiles, path=os.path.join(repo.path,sub),
                               force_creation=force_creation)
     else:
          makefiles = find_all_app_makefiles(repo.path)
          _check_cproject(repo, makefiles,
                          force_creation=force_creation)



def check_makefile(mkfile_path, repo, all_configs):
    updates_required = False
    relpath = os.path.relpath(mkfile_path,repo.path)
    flag_types, configs = get_configs(mkfile_path)
    if configs != all_configs:
        print "%s is missing flags for configs: %s" \
               %(relpath,' '.join(all_configs - configs))
        updates_required = True
    f = open(mkfile_path)
    lines = f.readlines()
    f.close()
    for line in lines:
        if re.match('all:.*',line):
            print "%s defines all target" % relpath
            updates_required = True
        if re.match('clean:.*',line):
            print "%s defines clean target" % relpath
            updates_required = True

        if re.match('\s*USED_MODULES\s*=.*module_(\w*)\.\d', line):
            print "%s has explicit module versions" % relpath
            updates_required = True

        m = re.match('-?include(.*)', line)
        if m:
            include_path = m.groups(0)[0].strip()
            if include_path != \
               '$(XMOS_MAKE_PATH)/xcommon/module_xcommon/build/Makefile.common':
                print "%s has incorrect xcommon include" % relpath
                updates_required = True

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
    in_config_branch = None
    newlines = []
    comments = []
    past_include = False
    for line in lines:
        skip_line = False
        m = re.match('\s*(XCC.*_FLAGS) (.*)',line)
        if in_config_branch and in_config_branch != '' and m:
            flags = m.groups(0)[0]
            rhs = m.groups(0)[1]
            line = '%s_%s %s\n' %(flags,in_config_branch,rhs)

        m = re.match('ifeq "\$\(CONFIG\)" "(\w*)"',line)
        if m:
            in_config_branch = m.groups(0)[0]
            skip_line = True

        if in_config_branch and re.match('.*endif',line):
            in_config_branch = None
            skip_line = True

        if in_config_branch and re.match('.*else',line):
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
            if line[0] == '#' or line == '\n' or re.match('XMOS_MAKE_PATH.*',line):
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

    for config in all_configs - configs:
        for flag_type in flag_types:
            if config == 'Default':
                newlines += "XCC%s_FLAGS = $(XCC%s_FLAGS%s)\n" \
                                         % (flag_type, flag_type, base_config)
            else:
                newlines += "XCC%s_FLAGS_%s = $(XCC%s_FLAGS%s)\n" \
                                          % (flag_type, config, flag_type, base_config)

    f = open(mkfile_path,"w")
    f.write(''.join(newlines) + include_section)
    f.close()

def check_toplevel_makefile(repo):
    print "Checking toplevel Makefile"
    updates_required = False
    path = os.path.join(repo.path,'Makefile')

    try:
         f = open(path)
    except:
         updates_required = True
         print "Toplevel Makefile does not exist"

    if not updates_required:
         lines = f.readlines()
         f.close()
         found_include = False
         for line in lines:
              if line == 'include $(XMOS_MAKE_PATH)/xcommon/module_xcommon/build/Makefile.toplevel\n':
                   found_include = True

         if not found_include:
              print "Toplevel Makefile incorrect"
              updates_required = True

    if updates_required:
        sys.stdout.write("There is a problem with the toplevel Makefile.\n")
        sys.stdout.write("Do you want xpd to create a new one (Y/n)?")
        x = raw_input()
        if not x in ['n','N','No','NO','no']:
             f = open(os.path.join(repo.path,'Makefile'),'w')
             f.write(templates.toplevel_makefile)
             f.close()
             print "New toplevel Makefile created"

    return updates_required

def check_makefiles(repo):
    updates_required = check_toplevel_makefile(repo)
    makefiles = find_all_app_makefiles(repo.path)
    all_configs = get_all_configs(makefiles)
    for mkfile in makefiles:
        print "Checking %s" % os.path.relpath(mkfile, repo.path)
        if flat_projects:
             configs = get_all_configs(set([mkfile]))
        else:
             configs = all_configs
        dirname = os.path.dirname(os.path.relpath(mkfile, repo.path))
        updates_required |= check_makefile(mkfile, repo, configs)
    if updates_required:
        print "Makefiles need updating. Do updates (Y/n)?"
        x = raw_input()
        if x not in ['N','n','No','NO','no']:
            for mkfile in makefiles:
                if flat_projects:
                       configs = get_all_configs(set([mkfile]))
                else:
                      configs = all_configs
                update_makefile(mkfile, configs)
                print "Updated %s" % os.path.relpath(mkfile, repo.path)

    return  (not updates_required)

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
