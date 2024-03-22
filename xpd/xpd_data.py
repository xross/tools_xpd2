import os, sys, re
import difflib
from xmlobject import XmlObject, XmlValue, XmlNode, XmlNodeList, XmlAttribute, XmlValueList, XmlText
from copy import copy
from xmos_subprocess import call, call_get_output
from xpd.check_project import find_all_subprojects, rst_title_regexp, is_non_xmos_project
from xmos_logging import log_error, log_warning, log_info, log_debug
import shutil
import tempfile
from docutils.core import publish_file
import xml.dom.minidom
from io import StringIO
from functools import total_ordering
from urllib.error import HTTPError
import urllib

xpd_version = "2.0"

DEFAULT_SCOPE='Experimental'

ORGANISATIONS=['xmos', 'xmos-int']

INCLUDE_BINARIES=['sw_']

def normalize_repo_uri(uri):
    if uri.find("github.com") == -1:
        return ""
    m = re.match(".*github.com[:/](.*)", uri)
    if not m:
        return uri
    return "git://github.com/" + m.groups(0)[0]

def normalize_repo_url(uri):
    if uri.find("github.com") == -1:
        return ""
    m = re.match(".*github.com[:/](.*)", uri)
    if not m:
        return uri
    return "www.github.com/" + re.sub('\.git$', '', m.groups(0)[0])

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

def changelog_str_to_version(version_str):
    try:
        version = Version(version_str=version_str)
    except VersionParseError:
        try:
            version = Version(version_str=version_str+'rc0')
        except VersionParseError:
            log_error("Can't parse version string %s in CHANGELOG" % v_str)
            return None
    return version

#FIXME handle version numbers

def get_project_immediate_deps(repo, project, is_update=False):
    def create_component_dependencies(modules_str, is_update):
      deps = []

      for module_str in modules_str.split(' '):
        if module_str in ["", "\\"]:
            continue

        module_name = module_str

        # Try and extract the version we want
        module_req_version = re.findall('\((.*?)\)', module_str)

        if module_req_version:
            module_req_version = module_req_version[0].strip()

            # Strip off version
            module_name = module_str.split('(')[0]

        dep = ComponentDependency()
        dep.module_name = module_name

        mrepo = repo.get_module_repo(module_name, is_update)

        if (mrepo):
            dep.repo = normalize_repo_uri(mrepo.location)
        else:
            # We are not currently tracking the repo so add it
            okay = repo.add_dep(module_name)

            if okay:
                mrepo = repo.get_module_repo(module_name, is_update)
                dep.repo = normalize_repo_uri(mrepo.location)

        version = repo.get_lib_version(module_name)


        if version:
            dep.version = version
            #dep.githash = repo.get_hash()
        else:
            dep.githash = mrepo.current_githash()

        if module_req_version:
            dep.required_version = RequiredVersion(module_req_version)

        deps.append(dep)
      return deps

    mkfile = os.path.join(repo.path,project,'Makefile')
    modinfo = os.path.join(repo.path,project,'module_build_info')
    deps = []

    in_modules = False

    if os.path.exists(modinfo):

        lines = open(modinfo).readlines()

        for i in range(0, len(lines)):

            line = lines[i]

            m = re.match('.*DEPENDENT_MODULES\s*[+]?=\s*(.*)',line)
            if m:

                modules_str = m.groups(0)[0]

                # Handle lists of modules with \
                line_ = line
                while(line_.strip().endswith("\\")):
                    i = i + 1
                    line_ = lines[i].strip()
                    modules_str = modules_str[:-1] + line_

                deps += create_component_dependencies(modules_str, is_update)

    if os.path.exists(mkfile):
        for line in open(mkfile).readlines():
            m = re.match('.*USED_MODULES\s*[+]?=\s*(.*)',line)
            if m:
                deps += create_component_dependencies(m.groups(0)[0], is_update)

    return deps


class VersionParseError(Exception):
    def __str__(self):
        return "VersionParseError"

@total_ordering
class Version(object):
    def __init__(self, major=0, minor=0, point=0,
                 rtype="release", rnumber=0,
                 version_str=None):

        self.branch_name = None
        self.branch_major = 0
        self.branch_minor = 0
        self.branch_point = 0
        self.branch_rnumber = 0

        if version_str == None:
            if rtype == "":
                rtype = "release"
            self.major = major
            self.minor = minor
            self.point = point
            self.rtype = rtype
            self.rnumber = rnumber
        else:
            self.parse_string(version_str)

    def parse_string(self, version_string):
        m = re.match(r'(\d*)\.(\d*)\.(\d*)(alpha|beta|rc|)(\d*)_([-\w*])_(\d*)\.(\d*)\.(\d*)(alpha|beta|rc|)(\d*)', version_string)

        if m:
            on_branch = True
        else:
            on_branch = False
            m = re.match(r'(\d*)\.(\d*)\.(\d*)(alpha|beta|rc|)(\d*)', version_string)
            if not m:
              m = re.match(r'([^v])v(\d)(\d?)(alpha|beta|rc|)(\d*)', version_string)

        if not m:
            raise VersionParseError

        self.major = int(m.groups(0)[0])
        self.minor = int(m.groups(0)[1])
        point = m.groups(0)[2]
        if point == '':
            point = '0'
        self.point = int(point)
        self.rtype = m.groups(0)[3]
        self.rnumber = m.groups(0)[4]
        if self.rnumber == "":
            self.rnumber = 0
        else:
            self.rnumber = int(self.rnumber)

        if on_branch:
            self.branch_name = m.groups(0)[5]
            self.branch_major = int(m.groups(0)[6])
            self.branch_minor = int(m.groups(0)[7])
            self.branch_point = int(m.groups(0)[8])
            self.branch_rtype = m.groups(0)[9]
            self.branch_rnumber = m.groups(0)[10]
            if self.branch_rnumber == "":
                self.branch_rnumber = 0
            else:
                self.branch_rnumber = int(self.branch_rnumber)

    def major_increment(self):
        return Version(self.major+1, 0, 0)

    def minor_increment(self):
        return Version(self.major, self.minor+1, 0)

    def point_increment(self):
        return Version(self.major, self.minor, self.point+1)

    def is_rc(self):
        if self.branch_name:
            return self.branch_rtype == 'rc'
        else:
            return self.rtype == 'rc'

    def is_full(self):
        return not self.branch_name and self.rtype in ['', 'release']

    def __lt__(self, other):
        return (self.major, self.minor, self.point) < (other.major, other.minor, other.point)

    def __eq__(self, other):
        return (self.major, self.minor, self.point) == (other.major, other.minor, other.point)

    def __hash__(self):
        return hash((self.major, self.minor, self.point))

    def __str__(self):
        vstr = ""
        rtype = self.rtype
        vstr = "%d.%d.%d" % (self.major, self.minor, self.point)
        if rtype not in ['', 'release']:
            vstr += "%s%d" % (self.rtype, self.rnumber)

        if self.branch_name:
            vstr += "_%s_%d.%d.%d" % (self.branch_name, self.branch_major, self.branch_minor, self.branch_point)

            if self.branch_rtype not in ['', 'release']:
              vstr += "%s%d" % (self.branch_rtype, self.branch_rnumber)

        return vstr

    def final_version_str(self):
        if self.branch_name:
            return "%d.%d.%d_%s_%d.%d.%d" % (self.major, self.minor, self.point, self.branch_name,
                                             self.branch_major, self.branch_minor, self.branch_point)
        else:
            return "%d.%d.%d" % (self.major, self.minor, self.point)

    def match_modulo_rnumber(self, other):
        return (self.major == other.major and
                self.minor == other.minor and
                self.point == other.point and
                self.rtype == other.rtype and
                not self.branch_name and
                not other.branch_name)

    def match_modulo_rnumber(self, other):
        return (self.major == other.major and
                self.minor == other.minor and
                self.point == other.point and
                self.rtype == other.rtype)

    def match_modulo_branch_rnumber(self, other):
        return (self.major == other.major and
                self.minor == other.minor and
                self.point == other.point and
                self.branch_name == other.branch_name and
                self.branch_major == other.branch_major and
                self.branch_minor == other.branch_minor and
                self.branch_point == other.branch_point and
                self.branch_type == other.branch_type)

    def set_branch_rnumber(self, releases):
        rels = [r for r in releases if self.match_modulo_branch_rnumber(r.version)]
        rels.sort()
        if not rels:
            self.rnumber = 0
        else:
            self.rnumber = rels[-1].version.rnumber + 1

    def set_rnumber(self, releases):
        rels = [r for r in releases if self.match_modulo_rnumber(r.version)]
        rels.sort()
        if not rels:
            self.rnumber = 0
        else:
            self.rnumber = rels[-1].version.rnumber + 1

    def equals_excluding_point(self, version_string):
        try:
           v2 = Version(version_str = str(version_string))
           return self.major == v2.major and self.minor == v2.minor
        except:
           return False


class RequiredVersion(Version):

    import operator

    operators = {
        '=' : operator.eq,
        '>' : operator.gt,
        '<' : operator.lt,
        '<=' : operator.le,
        '>=' : operator.ge
    }

    def __init__(self, version_str, **kwargs):

        if version_str[:1] in self.operators:
            self._op = version_str[:2]
            version_str = version_str[2:]
        elif version_str[0] in self.operators:
            self._op = version_str[0]
            version_str = version_str[1:]
        else:
            self._op = "="

        super().__init__(version_str = version_str, **kwargs)

    # Check a version meets this requirement
    def met_by(self, version: Version) -> bool:
        op_func = self.operators[self._op]
        return op_func(version, self)

    def __str__(self):
        return self._op + super().__str__()


class ComponentDependency():

    def __init__(self, version=None, required_version=None, githash=None, required_githash=None):

        self._version = version
        self._required_version = required_version
        self._githash = githash
        self._required_githash = required_githash
        self._repo = None

    #This is a string eg git://github.com/repo_name
    @property
    def repo(self):
        return self._repo

    @repo.setter
    def repo(self, r):
        self._repo = r

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, v):
        self._version = v

    @property
    def required_version(self):
        return self._required_version

    @required_version.setter
    def required_version(self, rv):
        self._required_version = rv

    @property
    def githash(self):
        return self._githash

    @property
    def githashshort(self):
        if self.githash:
            return self.githash[:8]
        return None

    @githash.setter
    def githash(self, g):
        self._githash = g

    @property
    def required_githash(self):
        return self._required_githash

    @required_githash.setter
    def required_githash(self, gh):
        self._required_githash = gh

    def __str__(self):
        if self.version:
            return "<ComponentDependency: %s (%s)>" % (self.module_name, str(self.version))
        else:
            return "<ComponentDependency: %s (%s)>" % (self.module_name, str(self.githashshort))

    def __repr__(self):
        return self.__str__()


class Dependency():
    #repo_name = XmlAttribute(attrname="repo", required=True)
    #uri = XmlValue(required=True)
    #githash = XmlValue(required=True)
    #gitbranch = XmlValue()
    #version_str = XmlValue(tagname="version")

    def __init__(self, parent, repo_name:str, repo=None):
        self._version = None
        self.parent = parent #Repo_()
        self.gitbranch = None
        self._repo_name = repo_name
        self._repo = repo

    @property
    def repo(self):
        return self._repo

    @repo.setter
    def repo(self, r):
        self._repo = r

    @property
    def uri(self):
        return self._repo.uri()

    @property
    def githash(self):
        return self._repo.current_githash()

    @property
    def repo_name(self):
        return self._repo_name

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, v):
        self._version = v

    def get_local_path(self):
        root_repo = self.parent
        return os.path.join(os.path.join(root_repo.path,".."),self.repo_name)

    def post_import(self):
        if self.gitbranch and "detached from" in self.gitbranch:
            self.gitbranch = None

        if os.path.exists(self.get_local_path()):
            path = os.path.abspath(self.get_local_path())

            (recursion, names) = self.parent.has_dependency_recursion()

            if recursion:
                log_error("Dependency recursion detected: %s" % ' -> '.join(names))
                sys.exit(1)
            elif path in self.parent._repo_cache:
                self._repo = self.parent._repo_cache[path]
            else:
                self._repo = Repo_(self.get_local_path(), parent=self.parent, parenthash=self.githash, create_master=True)
                self.parent._repo_cache[path] = self.repo

            if self._repo.current_gitbranch():
                self.gitbranch = self.repo.current_gitbranch()

        else:
            self._repo = None

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

@total_ordering
class Release_:

    def __init__(self, version_str=None, path=None, virtual=False, notes = None):

        self.version_str = version_str #TODO rm me. Use str(version)
        self.parenthash = None
        self.githash = None
        self.virtual = virtual
        self.path = path
        self.version = None
        self._notes = notes

        #print("Release("+version_str+")")
        if version_str:
            try:
                self.version = Version(version_str=self.version_str)
            except VersionParseError:
                raise VersionParseError

        if path:
            (self.githash, self.parenthash) = self._find_hashes()

    @property
    def notes(self):
        return self._notes

    @notes.setter
    def notes(self, n):
        self._notes = n

    def merge(self, other):
        #TODO - merge usecase and location info
        pass

    def __lt__(self, other):
        return self.version < other.version

    def __eq__(self, other):
        return self.version == other.version

    def _find_hashes(self):

        # Return hash at tag and parent
        (stdout_lines, stderr_lines) = call_get_output(["git", "rev-list", "-n", "1", "v"+str(self.version_str)], cwd=self.path)
        if stdout_lines:
            git_hash = stdout_lines[0].strip()
        else:
            git_hash = None

        (stdout_lines0, stderr_lines0) = call_get_output(["git", "rev-parse", git_hash+"^"], cwd=self.path)

        if stdout_lines0:
            parent_hash = stdout_lines0[0].strip()
        else:
            parent_hash = None

        return (git_hash, parent_hash)

    def __str__(self):
        return "<release:" + str(self.version) + ">"

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
    dependencies = XmlNodeList(ComponentDependency, tagname="componentDependency")
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
            self.description = "XMOS Software Lib: " + self.name

        if (os.path.exists(os.path.join(repo.path, path, self.id + '.metainfo'))):
            # Use '/' instead of os.path.join because otherwise the generated file is not
            # useable on linux if created on Windows
            self.metainfo_path = path + '/' + self.id + '.metainfo'
            self.buildresults_path = path + '/' + "." + self.id + '.buildinfo'

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
        xml_str = rst2xml(os.path.join(self.readme_path()))
        dom = xml.dom.minidom.parseString(xml_str)
        docnode = dom.getElementsByTagName('document')[0]
        fields['title'] = docnode.getAttribute('title')
        for field in dom.getElementsByTagName('field'):
            name_element = field.getElementsByTagName('field_name')[0]
            name = name_element.childNodes[0].data
            paras = field.getElementsByTagName('paragraph')
            value = ''
            for p in paras:
                if p.childNodes[0].nodeValue:
                    value += p.childNodes[0].data
            fields[name.lower()] = value
        return fields

    def __str__(self):
        return "<" + self.repo.name + ":" + self.name  + ">"

    def is_module(self):
        return re.match('module_.*',self.id) or re.match('lib_.*',self.id)

    def is_published(self):
        if self.repo.include_dirs != []:
            return self.name in self.repo.include_dirs
        if self.repo.exclude_dirs != []:
            return self.name not in self.repo.include_dirs
        return True

    def readme_path(self):

        read_me_path = os.path.join(self.repo.path, self.path, 'README.rst')

        if os.path.exists(read_me_path):
            return read_me_path

        read_me_path = os.path.join(self.repo.path, 'README.rst')

        if os.path.exists(read_me_path):
            return read_me_path

        return None



    def has_readme(self):
        return os.path.exists(self.readme_path())

class Repo_(XmlObject):
    dependencies = XmlNodeList(Dependency, tagname="dependency")
    #releases = XmlNodeList(Release_)
    longname = XmlValue(tagname="name")
    description = XmlValue()
    location = XmlValue()
    #xcore_repo = XmlValue()
    #docdirs = XmlValueList()
    exports = XmlValueList(tagname="binary_only")
    #git_export = XmlValue(default=False)
    vendor = "XMOS" #TODO allow for other vendors - get info from repo
    maintainer = XmlValue()
    keywords = XmlValueList()
    usecases = XmlNodeList(UseCase)
    #changelog = XmlNodeList(ChangeLog)
    partnumber = XmlValue()
    subpartnumber = XmlValue()
    #xcore_partnumber = XmlValue()
    #xcore_subpartnumber = XmlValue()
    domain = XmlValue()
    subdomain = XmlValue()
    licence = XmlValue()
    branched_from = XmlValue()
    include_dirs = XmlValueList()
    exclude_dirs = XmlValueList()
    tools = XmlValueList(tagname="tools")
    boards = XmlValueList()
    path = None

    def __init__(self, path, parenthash=None, master=False, create_master=False, git_export=True, **kwargs):
        path = os.path.abspath(path)
        self.path = path
        self.name = os.path.split(self.path)[-1]
        self.git = True
        self.sb = None
        self._git_export = git_export
        self.branched_from_version = None
        self._repo_cache = {self.path:self}
        self._components = []
        self._releases = []
        self._docdirs = []
        self.changelog_entries = []
        self.non_xmos_projects = []
        self.include_dirs = []
        self.exclude_dirs = []
        self._untracked_files = []
        self.snippets = []
        self.version_defines = []
        self.include_binaries = any(self.name.startswith(i) for i in INCLUDE_BINARIES)

        self._maintainers = self._find_maintainers()

        self.find_releases() # Populate self._releases

        self._find_docdirs() # Populates self._docdirs

        super(Repo_, self).__init__(**kwargs)

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
                #self.parseString(''.join(stdout_lines), src="%s:master:xpd.xml"%self.path)

        # TODO Rm me
        self.parseString("<xpd></xpd>")

        if not master and (not parenthash or create_master):
            self.master_repo = Repo_(self.path, master=True)
            self.merge_releases(self.master_repo)

    @property
    def git_export(self):
        return self._git_export

    @property
    def docdirs(self):
        return self._docdirs

    @property
    def releases(self):
        return self._releases

    @property
    def github_api_url(self):

        base_url = "https://api.github.com/repos/"
        uri = self.uri()

        if ".git" not in uri:
            uri = uri + ".git"

        if uri.find("github.com") == -1:
            return None

        m = re.match(".*github.com[:/](.*)\.git", uri)

        if m:
            user_repo = m.groups(0)[0]
        else:
            # TODO: handle
            raise

        api_url = base_url + user_repo + "/releases"
        return api_url

    @property
    def github_upload_url(self):

        base_url = "https://uploads.github.com/repos/"
        uri = self.uri()

        if ".git" not in uri:
            uri = uri + ".git"

        if uri.find("github.com") == -1:
            return None

        m = re.match(".*github.com[:/](.*)\.git", uri)
        user_repo = m.groups(0)[0]

        api_url = base_url + user_repo + "/releases"
        return api_url

    @property
    def github_user(self):

        uri = self.uri()

        if uri.find("github.com") == -1:
            return None

        m = re.match(".*github.com[:/](.*)/", uri)
        user_repo = m.groups(0)[0]

        return user_repo

    @property
    def maintainers(self):
        return self._maintainers

    @maintainers.setter
    def maintainers(self, c):
        raise Exception('I know Python!')
        self._maintainers = c
        #TODO write to CODEOWNERS

    @property
    def components(self):
        return self._components

    @components.setter
    def components(self, c):
        self._components = c

    def _find_docdirs(self):

        for root, dirs, files in os.walk(self.path):

            if "rst" in dirs:
                docpath = root
                if "_build" not in docpath:
                    self._docdirs.append(os.path.relpath(docpath, self.path))

    def find_releases(self):

        # RSO made this change to pickup releases on maintenence branches
        (stdout_lines, stderr_lines) = call_get_output(["git", "tag", "-l", "v*"], cwd=self.path)

        #(stdout_lines, stderr_lines) = call_get_output(["git", "tag", "--merged", "remotes/origin/master", "-l", "v*"], cwd=self.path)

        # try main
        #if stdout_lines == []:
        #    (stdout_lines, stderr_lines) = call_get_output(["git", "tag", "--merged", "remotes/origin/main", "-l", "v*"], cwd=self.path)

        for line in stdout_lines:
            line = str(line).replace('v','').replace('\n','')

            try:
                release = Release_(version_str=line, path=self.path)
                self._releases.append(release)
            except VersionParseError:
                log_warning(f'Bad version in tag: {str(line)}')

    def merge_releases(self, other):
        for rel_other in other.releases:
            rel = None
            for r in self._releases:
                if rel_other.version == r.version:
                    rel = r
            if rel:
                rel.merge(rel_other)
            else:
                self._releases.append(rel_other)

    # Returns all releases matching a certain verison (we could have 1.0.0alpha and 1.0.0beta for example)
    def get_releases(self, version):

        releases = []
        for r in self._releases:
            if r.version == version:
                releases.append(r)
        return releases

    def get_release(self, version):
        found = None
        for r in self._releases:
            if r.version == version:
                found = r
        return found

    def get_versioned_repo(self, version):
        rel = self.get_release(version)
        if not rel or not rel.parenthash:
            return None

        return Repo_(path=self.path, parenthash=rel.parenthash)

    # TODO this is quite fragile
    def _find_maintainers(self):

        codeowners_path = None
        if os.path.exists(os.path.join(self.path, "CODEOWNERS")):
            codeowners_path = os.path.join(self.path, "CODEOWNERS")

        if os.path.exists(os.path.join(self.path, ".github","CODEOWNERS")):
            codeowners_path = os.path.join(self.path, ".github", "CODEOWNERS")

        if not codeowners_path:
            return None

        with open(codeowners_path, "r") as f_ptr:
            lines = f_ptr.readlines()
            for l in lines:
                if l[0] == "*":
                    return l[1:].strip()

    # Should already of made tag by this point (we could check this)
    def create_github_release(self, gh, release):

        #TODO check it doesnt already exist
        url_suffix = self.github_api_url
        print(str(url_suffix))
        tag_name = "v"+str(release.version)
        name = tag_name
        body = "\n".join(release.notes)
        prerelease = False

        if any(pre in tag_name for pre in ('alpha', 'beta', 'rc')):
            prerelease = True

        try:
            gh.github_api_call(
                url_suffix=url_suffix,
                post_data={
                    "tag_name": tag_name,
                    "name": name,
                    "body": body,
                    "draft": False,
                    "prerelease": prerelease,
                },
            )
        except urllib.error.HTTPError:
            print(f"Could not create release! The tag {tag_name} may not exist of the release already exists")

    # Do not currently allow releases on anything but master
    # TODO release is a merge from current branch to master THEN tag
    def record_release(self, release):

        if self.git:
            ref = self.current_gitref()
            if ref != "master":

                #TODO make relase on upstream master
                #TODO git flow
                log_error("can only make releases from master")
                exit()
                error = self.git_checkout("master", silent=True)

                if error:
                    log_error("Could not checkout master branch")
                    return

                master_repo = Repo_(self.path)
                master_repo.releases.append(release)
                call(["git", "commit", "-m", "'Record release: %s'" % str(release.version)],
                                cwd=self.path, silent=True)
                self.git_checkout(ref, silent=True)

    def commit_release(self, release):

        print("commit_release")

        if self.git:
            call(["git", "commit", "-m", "'Release: %s'" % str(release.version)],
                            cwd=self.path, silent=True)
            print("done commit")
        else:
            print("self.git was none")
        self.record_release(release)

    def latest_release(self, release_filter=None):
        if release_filter:
            rels = [r for r in self._releases if release_filter(r)]
        else:
            rels = self._releases
        rels.sort()
        if rels != []:
            return rels[-1]
        return None

    def latest_full_release(self):
        return self.latest_release(release_filter=
                                   lambda r: r.version.is_full())

    def latest_pre_release(self):
        if self.branched_from_version:
            branch_name = self.current_gitbranch()
            return self.latest_release(release_filter=
                                       lambda r: not r.version.is_full() \
                                                 and r.version.branch_name == branch_name)
        else:
            return self.latest_release(release_filter=
                                       lambda r: not r.version.is_full() \
                                                 and not r.version.branch_name)

    def current_release(self):
        if not self.path:
            return None

        parent_hash = exec_and_match(["git","rev-parse","HEAD~1"],r'(.*)',cwd=self.path)

        rels = []
        for release in self._releases:
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

    # TODO remove this step
    def post_import(self):

        if self.longname == None:
            self.longname = self.name
        if self.location == None:
            self.location = self.uri()
        for comp in self.components:
            comp.repo = self

        self.parse_changelog()

        # Prune out releases not in change log
        # TODO warn?
        changelog_versions = []
        for (v,c) in self.changelog_entries:
            changelog_versions.append(v)
        self._releases = [r for r in self._releases if (str(r.version.final_version_str())) in changelog_versions]

        # TODO Prune out releases which are not valid - can't determine a version number or githash
        #self._releases = [r for r in self._releases if r.version or r.githash]

        # Cache the untracked files in this repo as it is a very common action to check whether untracked
        (stdout_lines, stderr_lines) = call_get_output(
                ["git", "status", "--porcelain", "--ignored"], cwd=self.path)

        self._untracked_files = []
        for line in stdout_lines + stderr_lines:
            m = re.match('^(?:\?\?|!!) (.*)', line)
            if m:
                self._untracked_files.append(m.group(1))

        if self.branched_from:
            try:
                self.branched_from_version = Version(version_str=self.branched_from)
            except VersionParseError:
                log_error("Unable to parse branched_from version %s - clearing field" % self.branched_from)
                self.branched_from = None

    def latest_version(self):
        rels = [r for r in self._releases \
                      if r.version and r.version.rtype=="release"]
        rels.sort()
        if rels == []:
            return Version(0,0,0)
        return rels[-1].version

    def get_local_modifications(self, is_dependency=False, unstaged_only=False):
        (stdout_lines, stderr_lines) = call_get_output(
                ["git", "update-index", "-q", "--refresh"], cwd=self.path)

        if unstaged_only:
            (stdout_lines, stderr_lines) = call_get_output(
                    ["git", "diff", "--name-only"], cwd=self.path)
        else:
            (stdout_lines, stderr_lines) = call_get_output(
                    ["git", "diff-index", "--name-only", "HEAD", "--"], cwd=self.path)

        # Ignore files which are changed by xpd unless it is a dependent repo which must have no changes
        if not is_dependency:
            stdout_lines = [ x.rstrip() for x in stdout_lines if not re.search("(^fatal:|\.xproject|\.cproject|\.project|xpd.xml)", x) ]

        return stdout_lines

    def has_local_modifications(self, is_dependency=False):
        if self.get_local_modifications(is_dependency=is_dependency):
            return True
        return False

    def is_untracked(self, path):
        if os.path.isdir(os.path.join(self.path, path)) and not path.endswith('/'):
            path = path + '/'

        if any([l for l in self._untracked_files if path == l]):
            return True
        return False

    # TODO cache URI on first discovery?
    def uri(self):
        uri = exec_and_match(["git","remote","show","-n","origin"],
                              r'.*Fetch URL: (.*)',
                              cwd=self.path)
        return uri

    def licence_is_general(self):
        if not self.licence or self.licence == 'general':
            return True

        return False

    def get_branched_from_version(self):
        return self.branched_from_version

    def set_branched_from(self, release_name):
        try:
            self.branched_from_version = Version(version_str=release_name)
            self.branched_from = release_name
        except VersionParseError:
            log_error("set_branched_from: unable to parse version %s" % release_name)

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
        branch = exec_and_match(["git","branch"],r'\* (.*)',cwd=self.path)

        if "detached from" in branch:
            return None

        return branch

    def all_repos(self):
        return [d.repo for d in self.get_all_deps_once()] + [self]

    def add_dep(self, name):

        if self.get_dependency(name):
            log_error("Dependency already exists")
            return False

        dep = Dependency(parent=self, repo_name=name)

        if not os.path.isdir(dep.get_local_path()):
            log_error("Cannot add dependency '%s' as folder '%s' does not exist" % (name, dep.get_local_path()))
            return False

        dep.repo = Repo_(dep.get_local_path())

        # RSO
        dep.post_import()

        rel = dep.repo.current_release()
        if rel:
            dep.version = rel.version

        self.dependencies.append(dep)
        if dep.version:
            log_info("%s added %s as dependency with uri: %s @ %s" % (self.name, name, dep.uri, dep.version))
        else:
            log_info("%s added %s as dependency with uri: %s" % (self.name, name, dep.uri))
        return True

    def remove_dep(self, name):
        for dep in self.dependencies:
            if dep.repo_name == name:
                self.dependencies.remove(dep)
                log_info("%s removed %s as dependency" % (self.name, name))
                return True

        log_error("%s is not a current dependency of %s" % (name, self.name))
        return False

    def get_child_hash(self, parenthash):
        return exec_and_match(["git","rev-list","--parents","--all"],
                              r'(.*) %s' % parenthash,
                              cwd=self.path)

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
        temp_repo_path = os.path.join(path,os.path.basename(self.path))
        if git_only:

            # Originally cloning from a local repo - but when the README is updated using this temp SB the URIs are wrong.
            # Ideally clone locally since this saves us some time and we can be offline...
            # For now use a half way house and use local as reference
            (stdout_lines, stderr_lines) = call_get_output(["git", "clone", "--reference", self.path, "--dissociate", self.uri()], cwd=path)
            # Note, tree-less clone to keep size down
            #(stdout_lines, stderr_lines) = call_get_output(["git", "clone", "--filter=tree:0", self.path], cwd=path)
            (stdout_lines, stderr_lines) = call_get_output(["git", "checkout", self.current_githash()], cwd=temp_repo_path)
        else:
            shutil.copytree(self.path, temp_repo_path)

        self._path = self.path
        self.path = os.path.join(path,self.name)
        self._prune_dirs()

    def orig_path(self):
        return self._path

    def move_to_temp_sandbox(self, git_only=True, shallow=False):
        dependencies = self.get_all_deps_once()
        self.sb = tempfile.mkdtemp()
        print(str(self.sb))
        self._move_to_temp_sandbox(self.sb,git_only=git_only)
        for dep in dependencies:
            if dep.repo:
                dep.repo._move_to_temp_sandbox(self.sb,git_only=git_only)

    def _restore_path(self):
        self.path = self._path

    def delete_temp_sandbox(self):
        self._restore_path()
        for dep in self.get_all_deps_once():
            if dep.repo:
                dep.repo._restore_path()
        shutil.rmtree(self.sb)

    # Return None of not on a version
    def get_lib_version(self, lib_name):
        repo_name = self.find_repo_containing_module(lib_name)
        if not repo_name:
            log_error('%s: 1 Unable to find repo containing depedency %s' %
                (self.name, lib_name))
            return None

        rel = None
        if repo_name == self.name:
            rel = self.current_release()
            #rel = self.latest_release()
        else:
            repo_dep = self.get_dependency(repo_name)
            if repo_dep and repo_dep.repo:
                #rel = repo_dep.repo.latest_release()
                rel = repo_dep.repo.current_release()

        if rel:
            #return rel.version.final_version_str()
            return rel.version

        return None

    def get_module_repo(self, module_name, is_update):
        repo_name = self.find_repo_containing_module(module_name)

        if not repo_name:
            log_error('%s: 2 Unable to find repo containing depedency %s' %
                (self.name, module_name))
            return None

        if repo_name == self.name:
            return self
        else:
            repo_dep = self.get_dependency(repo_name)

            if repo_dep and repo_dep.repo:
                return repo_dep.repo

        # Don't want this error message when this is an update that is going to fix it
        if not is_update:
            log_error('%s: 3 Unable to find repo containing depedency %s' %
                (self.name, module_name))

        return None

    def get_software_blocks_(self, path, is_update, search_for_deps):
        #path = self.path
        components = []
        for x in os.listdir(path):
            if x == 'doc':
                continue
            if x in self.exclude_dirs:
                continue
            if x in self.docdirs:
                continue
            if x.startswith('__'):
                continue
            if self.is_untracked(x):
                continue
            mkfile = os.path.join(path,x,'Makefile')
            modinfo = os.path.join(path,x,'module_build_info')
            if os.path.exists(mkfile) or os.path.exists(modinfo) or x == 'module_xcommon' or is_non_xmos_project(x, self) or re.match('^module_.*',x) or re.match('^lib_.*',x):
                comp = Component()
                comp.init_from_path(self, x)
                components.append(comp)
                if search_for_deps:
                    comp.dependencies = get_project_immediate_deps(self, os.path.join(path,x), is_update=is_update)
                    log_debug("Component %s has dependencies: %s" % (comp, comp.dependencies))

        return components

    def get_software_blocks(self, is_update=False, search_for_deps=True):

        components = self.get_software_blocks_(self.path, is_update, search_for_deps)

        # Currently we don't include dependencies of examples
        #if os.path.exists(os.path.join(self.path, "examples")):
        #    components += self.get_software_blocks_(os.path.join(self.path,"examples"), is_update, search_for_deps)
        return components

    def get_apps(self):
        return [x for x in self.get_software_blocks() if not x.is_module()]

    def get_libs(self):
        return [x for x in self.get_software_blocks() if x.is_module()]

    def get_modules(self):
        return self.get_libs()


    def get_dependency(self, dep_name):
        for dep in self.dependencies:
            if dep.repo.name == dep_name:
                return dep
        return None

    def assert_exists(self, dep):
        if not os.path.exists(dep.get_local_path()):
            rel = self.current_release()
            if rel:
              version_str = " version %s" % rel.version
              get_deps_str = " %s" % rel.version
            else:
              version_str = ""
              get_deps_str = ""

            log_error("Dependency missing: %s for %s%s" % (dep.repo_name, self.name, version_str))
            log_error("  - Use 'xpd get_deps%s' in %s to get dependent repositories" %
                (get_deps_str, self.name))
            sys.exit(1)

    def dep_iter(self, command, output_repo_names=True):
        deps = self.dependencies
        os.system(command)
        for dep in deps:
            cwd = os.getcwd()
            os.chdir(dep.get_local_path())
            if output_repo_names:
                log_info("\n"+str(dep)+":\n")
            os.system(command)
            os.chdir(cwd)

    def get_all_deps(self, clone_missing=False, ignore_missing=False):
        ''' A generator to get all dependencies recursively - will return the repo each time
            it is reached in traversing the dependency tree.
        '''
        for dep in self.dependencies:
            if clone_missing:
                parent = os.path.sep.join(os.path.split(self.path)[:-1])
                dep_path = os.path.join(parent, dep.repo_name)
                if not os.path.exists(dep_path):
                    if not dep.uri:
                        log_error("%s: Dependency %s has missing uri" %
                            (self.name, dep.repo_name))
                    else:
                        log_info("Cloning " + dep.repo_name)
                        call(["git", "clone", dep.uri, dep_path])
                        if dep.gitbranch and dep.gitbranch != "master":
                          call(["git", "checkout", "-b", dep.gitbranch, "origin/%s" % dep.gitbranch], cwd=dep_path)
                        self.assert_exists(dep)

                dep.post_import()
                if not dep.repo:
                    log_error("%s: Failed to create repo for dependency %s" %
                        (self.name, dep.repo_name))
                    continue
            else:
                if not ignore_missing:
                    self.assert_exists(dep)

            yield dep

            # If ignoring missing dependencies then the dependency repo may not exist
            if dep.repo:
              for d in dep.repo.get_all_deps(clone_missing=clone_missing,
                                             ignore_missing=ignore_missing):
                  yield d

    def get_all_deps_once(self):
        ''' Get all the dependencies but only return one instance per each repo name.
        '''
        deps = {}
        for dep in self.get_all_deps():
            if not dep.repo_name in deps:
                deps[dep.repo_name] = dep

        return list(deps.values())

    def get_all_deps_reversed_once(self):
        ''' Get all the dependencies but only return one instance per each repo name.
            Reverse the order so they should be deepest first
        '''
        dep_names = {}
        deps = []
        for dep in self.get_all_deps():
            if not dep.repo_name in dep_names:
                dep_names[dep.repo_name] = 1
            deps.append(dep)

        deps.reverse()
        return deps

    def clone_deps(self, version_name):
      if version_name == 'master':
        vrepo = self
      else:
        try:
          version = Version(version_str=version_name)
          vrepo = self.get_versioned_repo(version)
          if not vrepo:
            log_error("'%s' is not a known version" % version_name)
            return
        except VersionParseError:
          log_error("Failed to parse version '%s'" % version_name)
          return

      for dep in vrepo.get_all_deps(clone_missing=True):
        pass

    def checkout(self, version_name):
      if version_name == 'latest':
        rel = self.latest_release()
        if not rel:
          log_error("Cannot find latest release")
          sys.exit(1)
        else:
          log_info("Checking out %s" % str(rel.version))
          version = rel.version
      else:
        try:
          version = Version(version_str=version_name)
        except VersionParseError:
          self.dep_iter("git checkout %s" % version_name)
          return None

      rel = self.het_release(version)
      if not rel:
        log_error("Release '%s' not found" % version)
        sys.exit(1)

      githash = self.get_child_hash(rel.parenthash)
      if not githash:
        log_error("Cannot find githash for version %s, maybe the git history has been modified" % str(version))
        sys.exit(1)
      vrepo = self.get_versioned_repo(version)

      local_mod = False
      for dep in vrepo.get_all_deps_once():
        vrepo.assert_exists(dep)
        if dep.repo.has_local_modifications(is_dependency=True):
          log_error("%s has local modifications" % dep.repo_name)
          local_mod = True
      if local_mod:
        sys.exit(1)

      vrepo.git_checkout(githash)
      for dep in vrepo.get_all_deps_once():
        dep.repo.git_checkout(dep.githash)

      return vrepo

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
        retval = call(["git", "add", path], cwd=self.path, silent=True)
        if retval:
            log_error("'git add %s' failed" % path)

    def git_commit_if_changed(self, message, is_dependency=False):
        if self.has_local_modifications(is_dependency=is_dependency):
            call(["git", "commit", "-m", message], cwd=self.path, silent=True)

    def git_push_to_backup(self):
        retval = call(["git", "push", "--all", "-u", "origin"], cwd=self.path, silent=True)
        if retval:
          log_error("%s: failed to back up" % self.name)
        else:
          log_info("%s: successfully backed up" % self.name)

    def git_push(self):
        retval  = call(["git", "push", "--tags"], cwd=self.path, silent=True)
        retval |= call(["git", "push"], cwd=self.path, silent=True)
        if retval:
          log_error("%s: failed to push" % self.name)

    def git_fetch(self):
        retval = call(["git", "fetch"], cwd=self.path, silent=True)
        if retval:
          log_error("%s: failed to fetch" % self.name)

    def git_remove(self, path):
        call(["git", "rm", "-f", path], cwd=self.path, silent=True)

    def git_checkout(self, githash, silent=False):
        retval = call(["git", "checkout", githash], cwd=self.path, silent=silent)
        if retval:
          log_error("%s: failed to checkout %s" % (self.name, githash))
          return retval

    def git_tag(self, version_string):
        v = Version(version_str=version_string)

        print("git_tag: " + str(version_string))
        rel = self.get_release(v)
        print(str(rel))
        print(str(rel.parenthash))

        relhash = self.get_child_hash(rel.parenthash)
        print(str(relhash))

        if not relhash:
           log_error("Cannot determine release hash")
           sys.exit(1)

        call(["git", "tag", "v%s" % str(v), relhash], cwd=self.path)

    def git_diff(self, hash1, hash2, output_file=None):
        if output_file:
            (stdout_lines, stderr_lines) = call_get_output(
                    ["git", "diff", "-r", hash1, "-r", hash2], cwd=self.path)
            for line in stdout_lines + stderr_lines:
                output_file.write(line)

        else:
            call(["git", "diff", "-r", hash1, "-r", hash2], cwd=self.path)

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

        for proj, (repo, deps) in projs.items():
            for x in get_project_immediate_deps(repo, proj):
                deps.add(x)

        def find_untracked_deps(sub):
            parent_dir = os.path.join(self.path,'..')
            possible_repos = [d for d in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir,d))]
            for d in possible_repos:
                for x in os.listdir(os.path.join(parent_dir,d)):
                    if x == sub:
                        deps = set([])
                        repo = Repo_(os.path.join(parent_dir,d))
                        for y in get_project_immediate_deps(repo, x):
                            deps.add(y)

                        return (repo, deps)

            return (None, None)

        something_changed = True
        while (something_changed):
            something_changed = False
            for proj, (repo, deps) in projs.items():
                to_add = set([])
                update = None
                for dep in deps:
                    if dep.module_name in projs:
                        (_, dep_dep) = projs[dep.module_name]
                        to_add.update(dep_dep)
                    else:
                        (repo, dep_dep) = find_untracked_deps(dep.module_name)
                        if repo:
                            update = (dep.module_name, repo, dep_dep)
                            break

                if update:
                    something_changed = True
                    projs[update[0]] = (update[1], update[2])
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
        # Matches need to be either an exact match on the entire path
        # or a match with the trailing / to prevent folders which are
        # the same but then longer (e.g. test and test1) matching

        if self.include_dirs:
            # If there are any include_dirs then they take preference
            for include in self.include_dirs:
                match_path = os.path.join(self.path, include)
                match_path += '(' + re.escape(os.path.sep) + '.*)?$'
                if re.match(match_path, path):
                    return False
            return True

        for exclude in self.exclude_dirs:
            match_path = os.path.join(self.path, exclude)
            match_path += '(' + re.escape(os.path.sep) + '.*)?$'
            if re.match(match_path, path):
                return True
        return False

    def patch_version_defines(self, version):
        def walk_and_break(path):
            # Similar to os.walk, but allows the recursion to stop as soon as an untracked or excluded folder is found
            patched_files = set()
            for f in os.listdir(path):
                full_path = os.path.join(path, f)
                local_path = re.sub('^%s/' % self.path, '', full_path)
                if self.excluded(local_path):
                    continue
                if self.is_untracked(local_path):
                    continue

                if is_source_file(f):
                    file_patched = False
                    with open(full_path, "r") as f_ptr:
                        lines = f_ptr.readlines()
                    with open(full_path, "w") as f_ptr:
                        for line in lines:
                            (line, patched) = self.line_patch_version_defines(full_path, line, version)
                            file_patched |= patched
                            f_ptr.write(line.rstrip() + '\n')

                    if file_patched:
                        patched_files.add(self.relative_filename(full_path))

                elif os.path.isdir(full_path):
                    patched_files = patched_files | walk_and_break(full_path)

            return patched_files

        patched_files = walk_and_break(self.path)
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

    def parse_changelog(self):
        ''' Parse the changelog file and convert it to a map list of (version, items) entries.
            Also checks that there are no duplicate entries for the same version number
            and that the order of versions in the CHANGELOG is correct.
        '''
        self.changelog_entries = []

        changelog_path = os.path.join(self.path, 'CHANGELOG.rst')
        if not os.path.exists(changelog_path):
            log_warning("Cannot find CHANGELOG.rst in %s" % self.name)
            return

        with open(changelog_path) as f:
            lines = f.readlines()

        all_versions = set()
        current_version = None
        items = []
        for (i, line) in enumerate(lines):
            if i < len(lines)-1:
                next = lines[i+1]
            else:
                next = ''

            if re.match(rst_title_regexp, line):
                continue

            if "legacy release history" in line.lower():
                break

            try:
                v = Version(version_str=line.strip())
                if v in all_versions:
                    log_warning("%s: Duplicate release note entries for %s" %
                        (self.name, str(v)))
                all_versions.add(v)
            except VersionParseError:
                v = None

            if v:
                if current_version:
                    self.changelog_entries.append((str(current_version), items))
                current_version = v
                items = []
            else:
                #ignore blank lines
                if line.strip() != "":
                    items.append(line)

        if current_version:
            self.changelog_entries.append((str(current_version), items))

        # Add notes to each release object
        # TODO Pull into a different func?
        for c in self.changelog_entries:

            (current_version, notes) = c
            version = Version(version_str = current_version)
            releases = self.get_releases(version)
            for r in releases:
                r.notes = notes

    def find_repo_containing_module(self, module_name):
        root_dir = os.path.join(self.path, "..")

        for dep_repo in os.listdir(root_dir):
            repo_path = os.path.join(root_dir, dep_repo)
            if os.path.isdir(repo_path):
                for module_dir in os.listdir(repo_path):
                    if os.path.isdir(os.path.join(repo_path, module_dir)):
                        if module_dir == module_name:
                            return dep_repo
        return None

    #TODO tidy
    def find_repo_containing_module_path(self, module_name):
        root_dir = os.path.join(self.path, "..")

        for dep_repo in os.listdir(root_dir):
            repo_path = os.path.join(root_dir, dep_repo)
            if os.path.isdir(repo_path):
                for module_dir in os.listdir(repo_path):
                    if os.path.isdir(os.path.join(repo_path, module_dir)):
                        if module_dir == module_name:
                            return repo_path

        return None




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

