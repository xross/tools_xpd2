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

def new_id(m):
     return "id = \"" + m.groups(0)[0] + "." + str(rand.randint(0,100000000)) + "\""

def getFirstChild(node,tagname):
    for child in node.childNodes:
        if hasattr(child,'tagName') and child.tagName == tagname:
            return child
    return None

def check_project(repo):
    print "Checking .project file"
    project_ok = True
    project_path = os.path.join(repo.path,'.project')
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

        if not root:
            print ".project file is invalid"
            project_ok = False

        if project_ok:


            name_node = getFirstChild(root, 'name')

            try:
                valid_name = (name_node.childNodes[0].wholeText == repo.name)
            except:
                valid_name = False

            if not valid_name:
                print "Eclipse project name is invalid"
                project_ok = False

            projects = getFirstChild(root, 'projects')
            if projects and getFirstChild(projects, 'project'):
                print "Eclipse project has related projects in it (probably a bad idea)"
                project_ok = False

    if not project_ok:
        sys.stdout.write("There is a problem with the eclipse .project file.\n")
        sys.stdout.write("Do you want xpd to create a new one (Y/n)?")
        x = raw_input()
        if not x in ['n','N','No','NO','no']:
            project_lines = templates.dotproject.split('\n')
            f = open(os.path.join(repo.path,'.project'),'w')
            for line in project_lines:
                line = line.replace('%PROJECT%',repo.name)
                f.write(line)
            f.close()
            print "New .project created"
            project_ok = True

    return project_ok

def find_all_app_makefiles(repo):
    makefiles = set()
    for x in os.listdir(repo.path):
        if x[0:4] == 'app_':
            mkfile = os.path.join(repo.path,x,'Makefile')
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

def get_all_configs(repo):
    makefiles = find_all_app_makefiles(repo)
    configs = set(['Default'])
    for mkfile in makefiles:
        (_, mkfile_configs) = get_configs(mkfile)
        configs = configs | mkfile_configs

    if 'Debug' in configs:
        configs.add('Release')
    return configs

def create_cproject(repo, configs, all_includes=[]):
   cproject_path = os.path.join(repo.path,'.cproject')
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

   config_str = ''
   for config in configs:
       config_id = str(rand.randint(1,100000000))
       lines = templates.cproject_configuration.split('\n')
       if config == 'Default':
           config_args = ''
       else:
           config_args = 'CONFIG=%s'%config

       for i in range(len(lines)):
           lines[i] = lines[i].replace('%PROJECT%',repo.name)
           lines[i] = lines[i].replace('%CONFIG%',config)
           lines[i] = lines[i].replace('%CONFIG_ARGS%',config_args)
           lines[i] = lines[i].replace('%INCLUDES%',includes)
           lines[i] = re.sub(r'id\s*=\s*[\'"]([\w.]*)\.\d*[\'"]',new_id,lines[i])
           lines[i] = lines[i].replace('%CONFIG_ID%',config_id)

       config_str += '\n'.join(lines)

   lines = templates.cproject.split('\n')
   for i in range(len(lines)):
       lines[i] = lines[i].replace('%PROJECT%',repo.name)
       lines[i] = re.sub(r'id\s*=\s*[\'"]([\w.]*)\.\d*[\'"]',new_id,lines[i])
       lines[i] = lines[i].replace('%CONFIGURATIONS%',config_str)

   f = open(os.path.join(repo.path,'.cproject'),'w')
   f.write('\n'.join(lines))
   f.close()


def check_cproject(repo):
    print "Checking .cproject file"
    configs = get_all_configs(repo)
    if 'Debug' in configs and 'Release' in configs:
         configs.remove('Default')
    print "Using configs: %s" % ', '.join(configs)
    makefiles = find_all_app_makefiles(repo)
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
            sys.stderr.write("Cannot find xmake\n")
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


    all_includes = ['&quot;${workspace_loc:/%s}&quot;'%i \
                         for i in all_includes if i != '']

    sys_includes = ['&quot;${XMOS_DOC_PATH}/../target/include&quot;',
                    '&quot;${XMOS_TOOL_PATH}/target/include&quot;']

    print "Checking .cproject file"
    cproject_ok = True
    cproject_path = os.path.join(repo.path,'.cproject')
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

    if not cproject_ok:
        sys.stdout.write("There is a problem with the eclipse .cproject file.\n")
        sys.stdout.write("Do you want xpd to create a new one (Y/n)?")
        x = raw_input()
        if not x in ['n','N','No','NO','no']:
             create_cproject(repo, configs, all_includes)
             print "New .cproject created."

    return cproject_ok

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
    configs = get_all_configs(repo)
    makefiles = find_all_app_makefiles(repo)
    for mkfile in makefiles:
        print "Checking %s" % os.path.relpath(mkfile, repo.path)
        updates_required |= check_makefile(mkfile, repo, configs)
    if updates_required:
        print "Makefiles need updating. Do updates (Y/n)?"
        x = raw_input()
        if x not in ['N','n','No','NO','no']:
            for mkfile in makefiles:
                update_makefile(mkfile, configs)
                print "Updated %s" % os.path.relpath(mkfile, repo.path)

    return  (not updates_required)

def check_docdir(repo):
     pass
