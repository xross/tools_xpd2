import os, subprocess, sys, re
import difflib
from xmlobject import XmlObject, XmlValue, XmlNode, XmlNodeList, XmlAttribute, XmlValueList
from copy import copy

xpd_version = "1.0"
    

def exec_and_match(command, regexp, cwd=None):
    process = subprocess.Popen([command], cwd=cwd, shell=True, 
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    lines = process.stdout.readlines()
    for line in lines:
        m = re.match(regexp, line)
        if m:
            return m.groups(0)[0]
    return None

class Version(object):
    
    def __init__(self, major=0, minor=0, point=0, 
                 rtype="release",rnumber=0,
                 version_str = None):

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
        m = re.match(r'([^\.]*)\.([^\.]*)\.([^\.*])(alpha|beta|rc|)(\d*)', version_string)

        if not m:
            m = re.match(r'([^v])v(\d)(\d?)(alpha|beta|rc|)(\d*)', version_string)
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

        else:
            sys.stderr.write("ERROR: invalid version %s\n" % version_string)
            exit(1)

    def major_increment(self):
        return Version(self.major+1,0,0)

    def minor_increment(self):
        return Version(self.major,self.minor+1,0)

    def point_increment(self):
        return Version(self.major,self.minor,self.point+1)


    def is_full(self):
        return (self.rtype == 'release' or self.rtype=='')

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
        rtype = self.rtype
        if rtype=="release" or rtype=="":
            return "%d.%d.%d" % (self.major, self.minor, self.point)
        else:
            return "%d.%d.%d%s%d" % (self.major, self.minor, self.point,
                                     self.rtype, self.rnumber)

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
    repo_name = XmlAttribute(attrname="repo")
    uri = XmlValue()
    githash = XmlValue()
    gitbranch = XmlValue()
    version_str = XmlValue(tagname="version")

    def get_local_path(self):
        root_repo = self.parent
        return os.path.join(os.path.join(root_repo.path,".."),self.repo_name)

    def post_import(self):
        if os.path.exists(self.get_local_path()):
            path = os.path.abspath(self.get_local_path())
            if path in self.parent._repo_cache:
                self.repo = self.parent._repo_cache[path]
            else:                
                self.repo = Repo(self.get_local_path())
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
    version_str = XmlAttribute(attrname="version")
    parenthash = XmlAttribute()
    githash = XmlAttribute()
    location = XmlValue()
    usecases = XmlNodeList(UseCase)

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

        
class Repo(XmlObject):

    dependencies = XmlNodeList(Dependency, tagname="dependency")
    releases = XmlNodeList(Release)
    name = XmlValue()
    description = XmlValue()
    icon = XmlValue()
    location = XmlValue()
    doc = XmlValue()
    exports = XmlValueList(tagname="binary_only")
    git_export = XmlValue(default=True)
    xpd_version = XmlValue(default=xpd_version)
    release_notes = XmlNodeList(ReleaseNote)
    scope = XmlValue()
    vendor = XmlValue()
    maintainer = XmlValue()
    keywords = XmlValueList()
    usecases = XmlNodeList(UseCase)
    changelog = XmlNodeList(ChangeLog)
    
    path = None


    def __init__(self,path,parenthash=None,master=False,**kwargs):
        path = os.path.abspath(path)
        self.path = path
        self.git = True
        self._repo_cache = {self.path:self}
        super(Repo, self).__init__(**kwargs)

        process = subprocess.Popen(["git rev-parse --show-cdup"], shell=True,
                                   cwd=path,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        err_lines = process.stderr.readlines()
        lines = process.stdout.readlines()

        if err_lines != []:
            self.git = False

        if self.git or lines == []:
            git_dir = path
        else:
            git_dir = os.path.abspath(os.path.join(path,lines[0][:-1]))


        read_file = True

        if parenthash:
             relhash = self.get_child_hash(parenthash)
             process = subprocess.Popen(["git show %s:xpd.xml"%relhash], 
                                       shell=True,
                                       cwd=path,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            
             err_lines = process.stderr.readlines()
             if err_lines == []:
                      read_file = False            
                      self.parseString(process.stdout.read())


        if master:
             process = subprocess.Popen(["git show master:xpd.xml"], 
                                       shell=True,
                                       cwd=path,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            
             err_lines = process.stderr.readlines()
             if err_lines == []:
                      read_file = False            
                      self.parseString(process.stdout.read())

        self.xpd_file = os.path.join(git_dir,'xpd.xml')

        if read_file:
            try:
                self.parse(self.xpd_file)
            except IOError:
                self.parseString("<xpd></xpd>")
            
        if not master and not parenthash:
            master_repo = Repo(self.path,master=True)
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

        return Repo(path=self.path, 
                    parenthash = rel.parenthash)


    def checkout(self, githash, silent=False):
        if silent:
            subprocess.call(["git checkout %s"%githash],
                            shell=True,
                            cwd=self.path,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)            
        else:
            subprocess.call(["git checkout %s"%githash],
                            shell=True,
                            cwd=self.path)


            
    def save(self):
        f = open(self.xpd_file,"w")
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
                subprocess.call(["git add xpd.xml;git commit -m 'Record release: %s'"%str(release.version)],
                                shell=True,
                                cwd=self.path,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)                
                self.checkout(ref,silent=True)
            

    def save_and_commit_release(self, release):        
        self.save()
        if self.git:
            subprocess.call(["git add xpd.xml;git commit -m 'Release: %s'"%str(release.version)],
                            shell=True,
                            cwd=self.path,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

        self.record_release(release)

    def latest_release(self, release_filter = None):
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
                                   lambda r: not r.version.is_full())

                
    def current_release(self):
        if not self.path:
            return None
        parent_hash = exec_and_match("git rev-parse HEAD~1",r'(.*)',cwd=self.path)
        
        rels = []
        for release in self.releases:
            if hasattr(release,'parenthash') and parent_hash == release.parenthash:
               rels.append(release)

        rels.sort()

        if rels != []:
            return rels[-1]

        return None

    def post_import(self):
        if self.name == None:
            self.name = os.path.split(self.path)[-1]
        if self.location == None:
            self.location = self.uri()

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
        command = 'git update-index -q --refresh;git diff-index --name-only HEAD --'
        process = subprocess.Popen([command], cwd=self.path, shell=True, 
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        lines = process.stdout.readlines()
        if (lines == [] or re.match('fatal',lines[0])):
            return False
        return True

    def uri(self):
        return exec_and_match("git remote show -n origin",
                              r'.*Fetch URL: (.*)',
                              cwd=self.path)
        
    def current_gitref(self):
        symref = exec_and_match("git symbolic-ref HEAD",r'refs/heads/(.*)',
                                cwd=self.path)
        if symref == None:
            return self.current_githash()
        else:
            return symref
        

    def current_githash(self):
        return exec_and_match("git rev-parse HEAD",r'(.*)',cwd=self.path)
 
    def current_gitbranch(self):
        return exec_and_match("git branch",r'\* (.*)',cwd=self.path)

    def all_repos(self):
        return [d.repo for d in self.dependencies] + [self]

    def get_child_hash(self, parenthash):
        return exec_and_match("git rev-list --parents --all",
                              r'(.*) %s'%parenthash,
                              cwd=self.path)

    def get_release_notes(self, version):
        for rnote in self.release_notes:
            if rnote.version == version:
                return rnote
        else:
            return None

    def __str__(self):
        (_,name) = os.path.split(self.path)
        return name
