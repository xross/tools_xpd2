import os, subprocess, sys, re
import difflib
from xmlobject import XmlObject, XmlValue, XmlNode, XmlNodeList, XmlAttribute, XmlValueList
from copy import copy
from xpd.xpd_subprocess import call, call_get_output
from xpd.check_project import find_all_subprojects, get_project_immediate_deps
from xpd.xpd_logging import *
import shutil
import tempfile
from docutils.core import publish_file
import xml.dom.minidom
from StringIO import StringIO

xpd_version = "1.0"
    
DEFAULT_SCOPE='Experimental'

def rst2xml(path):
    """Convert restructured text to XML"""
    xml_file = StringIO()
    xml_file.close = lambda: None
    xml = publish_file(open(path),
                       writer_name='xml',
                       destination=xml_file)
    xml_file.seek(0)
    return xml_file.read()

def exec_and_match(command, regexp, cwd=None):
    (stdout_lines, stderr_lines) = call_get_output(command, cwd=cwd)
    for line in stdout_lines:
        m = re.match(regexp, line)
        if m:
            return m.groups(0)[0]
    return None

def is_source_file(filename):
    if (filename.endswith(".xc") or filename.endswith(".c") or
        filename.endswith(".h")  or filename.endswith(".S") or
        filename.endswith(".in")):
           return True
    return False


class VersionParseError(Exception):
    def __str__(self):
        return "VersionParseError"


class Version(object):
    def __init__(self, major=0, minor=0, point=0, 
                 rtype="release", rnumber=0,
                 branch=None, branch_rnumber=0,
                 version_str=None):

        if version_str == None:
            if rtype == "":
                rtype = "release"
            self.major = major
            self.minor = minor
            self.point = point
            self.rtype = rtype
            self.rnumber = rnumber
            self.branch = branch
            self.branch_rnumber = branch_rnumber
        else:
            self.parse_string(version_str)

    def parse_string(self, version_string):
        m = re.match(r'(\d*)\.(\d*)\.(\d*)(alpha|beta|rc|)(\d*)_?(\w*)(\d*)', version_string)

        if not m:
            m = re.match(r'([^v])v(\d)(\d?)(alpha|beta|rc|)(\d*)()()', version_string)
        if m:
            self.major = int(m.groups(0)[0]) 
            self.minor = int(m.groups(0)[1]) 
            point = m.groups(0)[2]
            if point == '':
                point = '0'
            self.point = int(point) 
            self.rtype = m.groups(0)[3]
            self.rnumber = m.groups(0)[4]
            if (self.rnumber == ""):
                self.rnumber = 0
            else:
                self.rnumber = int(self.rnumber)
            self.branch = m.groups(0)[5]
            if (self.branch == ""):
                self.branch = None
            else:
                self.branch = int(self.rnumber)

            self.branch_rnumber = m.groups(0)[6]
            if (self.branch_rnumber == ""):
                self.branch_rnumber = 0
            else:
                self.branch_rnumber = int(self.rnumber)

        else:
            raise VersionParseError

    def major_increment(self):
        return Version(self.major+1,0,0)

    def minor_increment(self):
        return Version(self.major,self.minor+1,0)

    def point_increment(self):
        return Version(self.major,self.minor,self.point+1)

    def is_full(self):
        return (not self.branch and (self.rtype == 'release' or self.rtype==''))

    def __cmp__(self, other):
        if other == None:
            return 1
        if self.major != other.major:
            return cmp(self.major, other.major)
        elif self.minor != other.minor:
            return cmp(self.minor, other.minor)
        elif self.point != other.point:
            return cmp(self.point, other.point)
        elif self.rtype != other.rtype:
            if self.rtype == '':
                return 1
            elif other.rtype == '':
                return -1
            else:            
                return cmp(self.rtype, other.rtype)
        else:
            if self.rtype in ['','release']:
                return 0
            else:
                return cmp(self.rnumber, other.rnumber)
            
    def __str__(self):
        vstr = ""
        rtype = self.rtype
        if rtype=="release" or rtype=="":
            vstr = "%d.%d.%d" % (self.major, self.minor, self.point)
        else:
            vstr = "%d.%d.%d%s%d" % (self.major, self.minor, self.point,
                                     self.rtype, self.rnumber)

        if self.branch:
            vstr += "_%s%d" % (self.branch, self.branch_rnumber)

        return vstr

    def final_version_str(self):
        vstr = "%d.%d.%d" % (self.major, self.minor, self.point)
        return vstr

    def match_modulo_rnumber(self, other):
        return (self.major == other.major and
                self.minor == other.minor and
                self.point == other.point and
                self.rtype == other.rtype)

    def match_modulo_rtype(self, other):
        return (self.major == other.major and
                self.minor == other.minor and
                self.point == other.point)

    def set_rnumber(self, releases):
        rels = [r for r in releases if self.match_modulo_rnumber(r.version)]
        rels.sort()
        if rels==[]:
            self.rnumber = 0
        else:
            self.rnumber = rels[-1].version.rnumber + 1


class Dependency(XmlObject):
    repo_name = XmlAttribute(attrname="repo", required=True)
    uri = XmlValue(required=True)
    githash = XmlValue(required=True)
    gitbranch = XmlValue()
    version_str = XmlValue(tagname="version")

    def get_local_path(self):
        root_repo = self.parent
        return os.path.join(os.path.join(root_repo.path,".."),self.repo_name)

    def post_import(self):
        if os.path.exists(self.get_local_path()):
            path = os.path.abspath(self.get_local_path())

            (recursion, names) = self.parent.has_dependency_recursion()

            if recursion:
                log_error("Dependency recursion detected: %s" % ' -> '.join(names))
                sys.exit(1)
            elif path in self.parent._repo_cache:
                self.repo = self.parent._repo_cache[path]
            else:                
                self.repo = Repo(self.get_local_path(), parent=self.parent)
                self.parent._repo_cache[path] = self.repo
        else:
            self.repo = None

    def __str__(self):
        return self.repo_name


class ToolVersion(XmlObject):
    pass


class ToolChainSection(XmlObject):
    tools = XmlValueList(tagname="tools")


class Board(XmlObject):
    is_schematic = False
    portmap = XmlAttribute()


class Schematic(Board):
    is_schematic = True


class HardwareSection(XmlObject):
    boards = XmlNodeList(Board)
    schematics = XmlNodeList(Schematic)
    

class DeviceSection(XmlObject):
    devices = XmlValueList()


class UseCase(XmlObject):
    name = XmlValue()
    usecase_type = XmlAttribute(attrname="type")
    toolchain = XmlNode(ToolChainSection, tagname="toolchain")
    hardware = XmlNode(HardwareSection, tagname="hardware")
    devices = XmlNode(DeviceSection, tagname="devices")
    description = XmlValue()
    

class Release(XmlObject):
    version_str = XmlAttribute(attrname="version", required=True)
    parenthash = XmlAttribute(required=True)
    githash = XmlAttribute()
    location = XmlValue()
    usecases = XmlNodeList(UseCase)
    warnings = XmlValueList()
    virtual = XmlAttribute()

    def post_import(self):
        if self.parenthash and not self.githash:
            self.githash = self.parent.get_child_hash(self.parenthash)
        if self.version_str:
            self.version = Version(version_str=self.version_str)
        else:
            self.version = None

    def pre_export(self):
        if hasattr(self,'version') and self.version != None:
            self.version_str = str(self.version)
        else:
            self.version_str = None

    def merge(self, other):
        #TODO - merge usecase and location info
        pass

    def __cmp__(self, other):
        if other == None:
            return 1
        else:
            return cmp(self.version, other.version)

    def __str__(self):
        return "<release:" + str(self.version) + ">"


class ReleaseNote(XmlObject):
    version_str = XmlAttribute(attrname="version")

    def post_import(self):
        if self.version_str:
            self.version = Version(version_str=self.version_str)
        else:
            self.version = None

    def __cmp__(self, other):
        return cmp(self.version, other.version)


class ChangeLog(XmlObject):
    version_str = XmlAttribute(attrname="version")

    def post_import(self):
        if self.version_str:
            self.version = Version(version_str=self.version_str)
        else:
            self.version = None


class VersionDefine(XmlObject):
    name = XmlAttribute()
    format = XmlAttribute()
    type = XmlAttribute()

    def produce_version_string(self, version):
        value_string = self.format
        value_string = value_string.replace("%MAJOR%", str(version.major))
        value_string = value_string.replace("%MINOR%", str(version.minor))
        value_string = value_string.replace("%POINT%", str(version.point))
        value_string = value_string.replace("%VERSION%", str(version))
        return value_string


class Component(XmlObject):
    id = XmlAttribute(required=True)
    name = XmlAttribute(required=True)
    description = XmlAttribute(required=True)
    metainfo_path = XmlAttribute()
    buildresults_path = XmlAttribute()
    scope = XmlAttribute(required=True)
    path = XmlAttribute(required=True)
    type = XmlAttribute(required=True)
    local = XmlAttribute()
    keywords = XmlValueList()
    boards = XmlValueList()
    docPartNumber = XmlAttribute()
    docVersion = XmlAttribute()
    dependencies = XmlValueList(tagname="componentDependency")
    zip_partnumber = XmlAttribute()

    def init_from_path(self, repo, path):
        self.id = os.path.basename(path)
        self.path = path
        self.repo = repo
        fields = self.readme_to_dict()
        if 'title' in fields and fields['title']:
            self.name = fields['title']
        else:
            self.name = self.id

        if 'scope' in fields:
            self.scope = fields['scope']
        else:
            self.scope = DEFAULT_SCOPE

        if 'keywords' in fields:
            self.keywords_text = fields['keywords']
            if self.keywords_text == '' or self.keywords_text[0] != '<':
                self.keywords = [x.strip() for x in fields['keywords'].split(',')]
        else:
            self.keywords_text = None
            self.keywords = []

        if 'boards' in fields:
            self.boards_text = fields['boards']
            if self.boards_text == '' or self.boards_text[0] != '<':
                self.boards = [x.strip() for x in fields['boards'].split(',')]
        else:
            self.boards_text = None
            self.boards = []

        if 'description' in fields:
            self.description = fields['description']
        else:
            self.description = "Software Block: " + self.name

        if (os.path.exists(os.path.join(repo.path,path,self.id+'.metainfo'))):
                self.metainfo_path = os.path.join(path,self.id+'.metainfo')
                self.buildresults_path = os.path.join(path,"."+self.id+".buildinfo")

        if self.metainfo_path:
            if self.id[0:4] == "app_":
                self.type = "applicationTemplate"
            else:
                self.type = "component"
        else:
            self.type = "demoCode"

        if self.scope == "Roadmap":
            if self.id[0:4] == "app_":
                self.type = "applicationTemplate"
            else:
                self.type = "component"

    def readme_to_dict(self):
        if not self.has_readme():
            return {}
        fields = {}
        xml_str = rst2xml(os.path.join(self.repo.path,self.path,'README.rst'))
        dom = xml.dom.minidom.parseString(xml_str)
        docnode = dom.getElementsByTagName('document')[0]
        fields['title'] = docnode.getAttribute('title')
        for field in dom.getElementsByTagName('field'):
            name_element = field.getElementsByTagName('field_name')[0]
            name = name_element.childNodes[0].data
            paras = field.getElementsByTagName('paragraph')
            value = ''
            for p in paras:
                value += p.childNodes[0].data
            fields[name] = value
        return fields

    def __str__(self):
        return "<" + self.repo.name + ":" + self.name  + ">"

    def is_module(self):
        return re.match('module_.*',self.id)

    def is_published(self):
        if self.repo.include_dirs != []:
            return self.name in self.repo.include_dirs
        if self.repo.exclude_dirs != []:
            return self.name not in self.repo.include_dirs
        return True

    def readme_path(self):
        return os.path.join(self.repo.path, self.path, 'README.rst')

    def has_readme(self):
        return os.path.exists(self.readme_path())


class Repo(XmlObject):
    dependencies = XmlNodeList(Dependency, tagname="dependency")
    releases = XmlNodeList(Release)
    longname = XmlValue(tagname="name")
    description = XmlValue()
    icon = XmlValue()
    location = XmlValue()
    xcore_repo = XmlValue()
    docdirs = XmlValueList()
    exports = XmlValueList(tagname="binary_only")
    git_export = XmlValue(default=False)
    include_binaries = XmlValue(default=False)
    xpd_version = XmlValue(default=xpd_version)
    release_notes = XmlNodeList(ReleaseNote)
    vendor = XmlValue()
    maintainer = XmlValue()
    keywords = XmlValueList()
    usecases = XmlNodeList(UseCase)
    changelog = XmlNodeList(ChangeLog)
    partnumber = XmlValue()
    subpartnumber = XmlValue()
    xcore_partnumber = XmlValue()
    xcore_subpartnumber = XmlValue()
    domain = XmlValue()
    subdomain = XmlValue()
    include_dirs = XmlValueList()
    exclude_dirs = XmlValueList()
    xsoftip_excludes = XmlValueList()
    tools = XmlValueList(tagname="tools")
    boards = XmlValueList()
    extra_eclipse_projects = XmlValueList()
    components = XmlNodeList(Component, wrapper="components")
    version_defines = XmlNodeList(VersionDefine, wrapper="version_defines")
    snippets = XmlValue(default=False)
    docmap_partnumber = XmlValue()
    path = None

    def __init__(self, path, parenthash=None, master=False, **kwargs):
        path = os.path.abspath(path)
        self.path = path
        self.name = os.path.split(self.path)[-1]
        self.git = True
        self.sb = None
        self._repo_cache = {self.path:self}
        super(Repo, self).__init__(**kwargs)

        (stdout_lines, stderr_lines) = call_get_output(
                ["git", "rev-parse", "--show-cdup"], cwd=path)

        if any("fatal: Not a git repo" in s for s in stderr_lines):
            log_error('No git repo found in %s' % path)
            sys.exit(1)

        if self.git or stdout_lines == []:
            git_dir = path
        else:
            git_dir = os.path.abspath(os.path.join(path, stdout_lines[0][:-1]))

        read_file = True

        if parenthash:
            relhash = self.get_child_hash(parenthash)
            (stdout_lines, stderr_lines) = call_get_output(
                    ["git", "show", "%s:xpd.xml" % relhash], cwd=path)
            
            if stderr_lines == []:
                read_file = False
                self.parseString(''.join(stdout_lines), src="%s:%s:xpd.xml" % (self.path,relhash))

        if master:
            (stdout_lines, stderr_lines) = call_get_output(
                    ["git", "show", "master:xpd.xml"], cwd=path)

            if stderr_lines == []:
                read_file = False
                self.parseString(''.join(stdout_lines), src="%s:master:xpd.xml"%self.path)

        self.xpd_file = os.path.join(git_dir,'xpd.xml')

        if read_file:
            try:
                self.parse(self.xpd_file)
            except IOError:
                self.parseString("<xpd></xpd>")
            
        if not master and not parenthash:
            master_repo = Repo(self.path, master=True)
            self.merge_releases(master_repo)

    def merge_releases(self, other):
        for rel_other in other.releases:
            rel = None
            for r in self.releases:
                if rel_other.version == r.version:
                    rel = r
            if rel:
                rel.merge(rel_other)
            else:
                self.releases.append(rel_other)

    def get_release(self, version):
        found = None
        for r in self.releases:
            if r.version == version:
                found = r
        return found

    def get_versioned_repo(self, version):
        rel = self.get_release(version)
        if not rel or not rel.parenthash:
            return None

        return Repo(path=self.path, parenthash=rel.parenthash)

    def checkout(self, githash, silent=False):
        call(["git", "checkout",githash], cwd=self.path, silent=silent)
            
    def save(self):
        log_debug("Saving xpd.xml") 
        f = open(self.xpd_file, 'wb')
        f.write(self.toxml("xpd"))
        f.close()
            
    def record_release(self, release):
        if self.git:
            ref = self.current_gitref()
            if ref != "master":
                self.checkout("master",silent=True)
                master_repo = Repo(self.path)
                master_repo.releases.append(release)   
                master_repo.save()
                call(["git", "add", "xpd.xml"], cwd=self.path, silent=True)
                call(["git", "commit", "-m", "'Record release: %s'" % str(release.version)],
                                cwd=self.path, silent=True)
                self.checkout(ref, silent=True)

    def save_and_commit_release(self, release):
        self.save()
        if self.git:
            call(["git", "add", "xpd.xml"], cwd=self.path, silent=True)
            call(["git", "commit", "-m", "'Release: %s'" % str(release.version)],
                            cwd=self.path, silent=True)

        self.record_release(release)

    def latest_release(self, release_filter=None):
        if release_filter:
            rels = [r for r in self.releases if release_filter(r)]
        else:
            rels = self.releases
        rels.sort()
        if rels != []:
            return rels[-1]
        return None                

    def latest_full_release(self):
        return self.latest_release(release_filter=
                                   lambda r: r.version.is_full())

    def latest_pre_release(self):
        return self.latest_release(release_filter=
                                   lambda r: not r.version.is_full() \
                                             and not r.version.branch)

    def current_release(self):
        if not self.path:
            return None
        parent_hash = exec_and_match(["git","rev-parse","HEAD~1"],r'(.*)',cwd=self.path)
        
        rels = []
        for release in self.releases:
            if hasattr(release,'parenthash') and parent_hash == release.parenthash:
               rels.append(release)

        rels.sort()

        if rels != []:
            return rels[-1]

        return None

    def current_version_or_githash(self, short=False):
        rel = self.current_release()
        if rel:
            vstr = str(rel.version)
        else:
            if short:
                vstr = self.current_githash()[:8]
            else:
                vstr = self.current_githash()
        return vstr

    def post_import(self):
        if self.longname == None:
            self.longname = self.name
        if self.location == None:
            self.location = self.uri()
        for comp in self.components:
            comp.repo = self

        # Prune out releases which are not valid - can't determine a version number or githash
        self.releases = [r for r in self.releases if r.version or r.githash]

        for exclude in self.xsoftip_excludes:
            if not os.path.exists(os.path.join(self.path, exclude)):
                log_error("%s: xsoftip_exclude '%s' does not exist" % (self.name, exclude))

    def pre_export(self):
        self.xpd_version = xpd_version

    def latest_version(self):
        rels = [r for r in self.releases \
                      if r.version and r.version.rtype=="release"]
        rels.sort()
        if rels == []:
            return Version(0,0,0)
        return rels[-1].version

    def has_local_modifications(self):
        (stdout_lines, stderr_lines) = call_get_output(
                ["git", "update-index", "-q", "--refresh"], cwd=self.path)

        (stdout_lines, stderr_lines) = call_get_output(
                ["git", "diff-index", "--name-only", "HEAD", "--"], cwd=self.path)

        # Ignore files which are changed by xpd
        stdout_lines = [ x for x in stdout_lines if not re.search("(^fatal:|\.xproject|\.cproject|xpd.xml)", x) ]

        if stdout_lines:
            return True
        return False

    def uri(self):
        return exec_and_match(["git","remote","show","-n","origin"],
                              r'.*Fetch URL: (.*)',
                              cwd=self.path)
        
    def current_gitref(self):
        symref = exec_and_match(["git","symbolic-ref","HEAD"],r'refs/heads/(.*)',
                                cwd=self.path)
        if symref == None:
            return self.current_githash()
        else:
            return symref

    def is_detached_head(self):
        symref = exec_and_match(["git","symbolic-ref","HEAD"],r'refs/heads/(.*)',
                                cwd=self.path)
        return (symref == None)

    def current_githash(self):
        return exec_and_match(["git","rev-parse","HEAD"],r'(.*)',cwd=self.path)
 
    def current_gitbranch(self):
        return exec_and_match(["git","branch"],r'\* (.*)',cwd=self.path)

    def all_repos(self):
        return [d.repo for d in self.dependencies] + [self]

    def get_child_hash(self, parenthash):
        return exec_and_match(["git","rev-list","--parents","--all"],
                              r'(.*) %s' % parenthash,
                              cwd=self.path)

    def get_release_notes(self, version):
        for rnote in self.release_notes:
            if rnote.version == version:
                return rnote
        else:
            return None

    def is_xmos_repo(self):
        if self.vendor and re.match(r'.*XMOS.*',self.vendor.upper()):
            return True
        else:
            return False

    def __str__(self):
        (_,name) = os.path.split(self.path)
        return name

    def _prune_dirs(self):
        all_dirs = [x for x in os.listdir(self.path) if
                                   os.path.isdir(os.path.join(self.path,x))]
        includes = copy(all_dirs)
        if self.include_dirs != []:
            includes = [x for x in includes if x in self.include_dirs]
        includes = [x for x in includes if not x in self.exclude_dirs]
        excludes = [x for x in all_dirs if not x in includes]
        for d in excludes:
            shutil.rmtree(os.path.join(self.path,d))

    def _move_to_temp_sandbox(self, path, git_only=True):
        if git_only:
            (stdout_lines, stderr_lines) = call_get_output(
                    ["git", "clone", self.path], cwd=path)
            (stdout_lines, stderr_lines) = call_get_output(
                    ["git", "checkout", self.current_githash()], cwd=path)
        else:
            shutil.copytree(self.path, os.path.join(path,os.path.basename(self.path)))

        self._path = self.path
        self.path = os.path.join(path,self.name)
        self._prune_dirs()

    def orig_path(self):
        return self._path

    def move_to_temp_sandbox(self,git_only=True):
        self.sb = tempfile.mkdtemp()
        self._move_to_temp_sandbox(self.sb,git_only=git_only)
        for dep in self.dependencies:
            if dep.repo:
                dep.repo._move_to_temp_sandbox(self.sb,git_only=git_only)

    def _restore_path(self):
        self.path = self._path

    def delete_temp_sandbox(self):
        self._restore_path()
        for dep in self.dependencies:
            if dep.repo:
                dep.repo._restore_path()
        shutil.rmtree(self.sb)

    def get_software_blocks(self):
        path = self.path
        components = []
        for x in os.listdir(path):
          if x == 'doc':
              continue
          if x in self.exclude_dirs:
              continue
          if x in self.docdirs:
              continue
          if x in self.xsoftip_excludes:
              continue
          if x.startswith('__'):
              continue
          mkfile = os.path.join(path,x,'Makefile')
          modinfo = os.path.join(path,x,'module_build_info')
          if os.path.exists(mkfile) or os.path.exists(modinfo) or x == 'module_xcommon' or (x in self.extra_eclipse_projects) or re.match('^module_.*',x):
              comp = Component()
              comp.init_from_path(self, x)
              components.append(comp)
              if os.path.exists(modinfo):
                  for line in open(modinfo).readlines():
                      m = re.match('.*DEPENDENT_MODULES\s*=\s*(.*)',line)
                      if m:
                          comp.dependencies += [x.strip() for x in m.groups(0)[0].split(' ')]
              if os.path.exists(mkfile):
                  for line in open(mkfile).readlines():
                      m = re.match('.*USED_MODULES\s*=\s*(.*)',line)
                      if m:
                          comp.dependencies += [x.strip() for x in m.groups(0)[0].split(' ')]

        return components

    def get_apps(self):
        return [x for x in self.get_software_blocks() if not x.is_module()]

    def get_modules(self):
        return [x for x in self.get_software_blocks() if x.is_module()]

    def create_dummy_package(self, version_str):
        package = Package()
        package.id = "xm-local-" + self.name
        package.hash = "DUMMY-HASH"
        package.latestversion = version_str
        package.version = version_str
        package.name = package.id + "(" + package.version + ")"
        package.packagename = package.id + "(" + package.version + ").zip"
        package.project = self.name
        package.description = self.description
        package.components = [copy(c) for c in self.components]
        package.authorised = "true"
        return package

    def git_add(self, path):
        call(["git","add",path], cwd=self.path, silent=True)

    def git_push(self):
        call(["git","push"], cwd=self.path, silent=True)

    def git_fetch(self):
        call(["git","fetch"], cwd=self.path, silent=True)

    def git_remove(self, path):
        call(["git","rm","-f",path], cwd=self.path, silent=True)

    def behind_upstream(self):
        (stdout_lines, stderr_lines) = call_get_output(
                ["git", "status", "-uno"], cwd=self.path)

        for line in stdout_lines:
            if re.match('.*is behind*', line):
                return True
            if re.match('.*diverged*', line):
                return True

        return False

    def enter_github_mode(self):
        log_info("Github mode")
        self._partnumber = self.partnumber
        self._subpartnumber = self.subpartnumber
        self.partnumber = self.xcore_partnumber
        self.subpartnumber = self.xcore_subpartnumber

    def leave_github_mode(self):
        self.xcore_partnumber = self.partnumber
        self.xcore_subpartnumber = self.subpartnumber
        self.partnumber = self._partnumber
        self.subpartnumber = self._subpartnumber

    def get_project_deps(self):
        projs = {}
        for repo in self.all_repos():
            if repo:
                for sub in find_all_subprojects(repo):
                    projs[sub] = (repo, set([]))

        for proj, (repo, deps) in projs.iteritems():
            for x in get_project_immediate_deps(repo, proj):
                if x != '':
                    deps.add(x)

        def find_untracked_deps(sub):
            parent_dir = os.path.join(self.path,'..')
            possible_repos = [d for d in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir,d))]
            for d in possible_repos:
                for x in os.listdir(os.path.join(parent_dir,d)):
                    if x==sub:
                        deps = set([])
                        repo = Repo(os.path.join(parent_dir,d))
                        for y in get_project_immediate_deps(repo, x):
                            if y != '':
                                deps.add(y)

                        return (repo,deps)

            return None,None

        something_changed = True
        while (something_changed):
            something_changed = False
            for proj, (repo, deps) in projs.iteritems():
                to_add = set([])
                update = None
                for dep in deps:
                    if dep in projs:
                        (_,dep_dep) = projs[dep]
                        to_add.update(dep_dep)
                    else:
                        (repo,dep_dep) = find_untracked_deps(dep)
                        if repo:
                            update = (dep, repo, dep_dep)
                            break

                if update:
                    something_changed = True
                    projs[update[0]] = (update[1],update[2])
                    break

                if not to_add.issubset(deps):
                    deps.update(to_add)
                    something_changed = True

        return projs

    def find_swblock(self, id):
        for swblock in self.components:
            if swblock.id == id:
                return swblock
        return None

    def excluded(self, path):
        # If there are any include_dirs then they take preference
        if self.include_dirs:
            for include in self.include_dirs:
                match_path = os.path.join(self.path, exclude, '.*')
                if re.match(match_path, path):
                    return False
            return True

        for exclude in self.exclude_dirs:
            match_path = os.path.join(self.path, exclude, '.*')
            if re.match(match_path, path):
                return True
        return False

    def patch_version_defines(self, version):
        patched_files = set()
        for root, dirs, files in os.walk(self.path):
            if self.excluded(root):
                continue

            source_files = [f for f in files if is_source_file(f)]

            for f in source_files:
                file_patched = False
                filename = os.path.join(root, f)
                with open(filename, "r") as f_ptr:
                    lines = f_ptr.readlines()
                with open(filename, "wb") as f_ptr:
                    for line in lines:
                        (line, patched) = self.line_patch_version_defines(filename, line, version)
                        file_patched |= patched
                        f_ptr.write(line)

                if file_patched:
                    patched_files.add(self.relative_filename(filename))

        return patched_files

    def line_patch_version_defines(self, filename, line, version):
        if not re.search("^\s*#\s*define", line):
            return (line, False)

        patched = False
        for version_define in self.version_defines:
            m = re.match('^(\s*)#(\s*)define(\s+)%s(\s+)[^\s]+(.*)$' % version_define.name, line)
            if m:
                value = version_define.produce_version_string(version)
                if version_define.type == "str":
                    value = '"' + value + '"'

                log_debug("Patching %s %s = %s" % (self.relative_filename(filename), version_define.name, value))
                line = '%s#%sdefine%s%s%s%s%s\n' % (m.group(1), m.group(2), m.group(3),
                        version_define.name, m.group(4), value, m.group(5))
                patched = True
                break

        return (line, patched)

    def relative_filename(self, filename):
        relative_filename = re.sub("^%s%s" % (os.path.commonprefix([filename, self.path]), os.sep), '', filename)
        return relative_filename

    def has_dependency_recursion(self):
        recursion = False
        names = [ self.name ]
        parent = self.parent
        while parent:
            if parent:
                names.insert(0, parent.name)
                if parent.name == self.name:
                    recursion = True
            parent = parent.parent

        return (recursion, names)


class Package(XmlObject):
    name = XmlAttribute()
    id = XmlAttribute()
    hash = XmlAttribute()
    project = XmlAttribute()
    authorised = XmlAttribute()
    packagename = XmlAttribute()
    latestversion = XmlAttribute()
    version = XmlAttribute()
    description = XmlValue()
    components = XmlNodeList(Component, wrapper="components")


class AllSoftwareDescriptor(XmlObject):
    packages = XmlNodeList(Package)
    toolsVersion = XmlAttribute()


class SoftwareDescriptor(XmlObject):
    packages = XmlNodeList(Package)
    toolsVersion = XmlAttribute()
    id = XmlAttribute()
    project = XmlAttribute()
    name = XmlAttribute()


class Doc(XmlObject):
    category = XmlAttribute()
    subcategory = XmlAttribute()
    partnumber = XmlAttribute()
    appname = XmlAttribute()
    related = XmlValueList()
    title = XmlAttribute()


class DocMap(XmlObject):
    docs = XmlNodeList(Doc)

