
from xmlobject import XmlObject, XmlValue, XmlNode, XmlNodeList, XmlAttribute, XmlValueList, XmlText
from xpd.xpd_data import Release, Version, Dependency, ReleaseNote, UseCase, ChangeLog, Component, VersionDefine, VersionParseError, exec_and_match
import os, sys, re
from xmos_subprocess import call, call_get_output
from xpd.check_project import find_all_subprojects, rst_title_regexp, is_non_xmos_project
from xpd.xpd_data import get_project_immediate_deps
from xmos_logging import log_error, log_warning, log_info, log_debug

class Repo_(XmlObject):
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
    #xpd_version = XmlValue(default=xpd_version)
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
    licence = XmlValue()
    branched_from = XmlValue()
    include_dirs = XmlValueList()
    exclude_dirs = XmlValueList()
    xsoftip_excludes = XmlValueList()
    tools = XmlValueList(tagname="tools")
    boards = XmlValueList()
    extra_eclipse_projects = XmlValueList()
    non_xmos_projects = XmlValueList()
    #components = XmlNodeList(Component, wrapper="components")
    version_defines = XmlNodeList(VersionDefine, wrapper="version_defines")
    snippets = XmlValue(default=False)
    docmap_partnumber = XmlValue()
    path = None
    no_xsoftip = XmlValue(default=False)

    def __init__(self, path, parenthash=None, master=False, create_master=False, **kwargs):
        path = os.path.abspath(path)
        self.path = path
        self.name = os.path.split(self.path)[-1]
        self.git = True
        self.sb = None
        self.branched_from_version = None
        self._repo_cache = {self.path:self}
        self._components = []
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
                self.parseString(''.join(stdout_lines), src="%s:master:xpd.xml"%self.path)

        self.xpd_file = os.path.join(git_dir,'xpd.xml')

        if read_file:
            #try:
            #    self.parse(self.xpd_file)
            #except IOError:
            self.parseString("<xpd></xpd>")

        if not master and (not parenthash or create_master):
            self.master_repo = Repo_(self.path, master=True)
            self.merge_releases(self.master_repo)

    @property
    def components(self):
        return self._components

    @components.setter
    def components(self, c):
        self._components = c

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

        return Repo_(path=self.path, parenthash=rel.parenthash)

    def save(self):
        log_debug("Saving xpd.xml")
        f = open(self.xpd_file, 'wb')
        f.write(self.toxml("xpd"))
        f.close()

    def record_release(self, release):
        if self.git:
            ref = self.current_gitref()
            if ref != "master":
                self.git_checkout("master", silent=True)
                master_repo = Repo_(self.path)
                master_repo.releases.append(release)
                master_repo.save()
                call(["git", "add", "xpd.xml"], cwd=self.path, silent=True)
                call(["git", "commit", "-m", "'Record release: %s'" % str(release.version)],
                                cwd=self.path, silent=True)
                self.git_checkout(ref, silent=True)

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

        self.parse_changelog()

        for exclude in self.xsoftip_excludes:
            if not os.path.exists(os.path.join(self.path, exclude)):
                log_warning("%s: xsoftip_exclude '%s' does not exist" % (self.name, exclude))

        # Cache the untracked files in this repo as it is a very common action to check whether untracked
        (stdout_lines, stderr_lines) = call_get_output(
                ["git", "status", "--porcelain", "--ignored"], cwd=self.path)

        self.untracked_files = []
        for line in stdout_lines + stderr_lines:
            m = re.match('^(?:\?\?|!!) (.*)', line)
            if m:
                self.untracked_files.append(m.group(1))

        if self.branched_from:
            try:
                self.branched_from_version = Version(version_str=self.branched_from)
            except VersionParseError:
                log_error("Unable to parse branched_from version %s - clearing field" % self.branched_from)
                self.branched_from = None

    #def pre_export(self):
    #    self.xpd_version = xpd_version

    def latest_version(self):
        rels = [r for r in self.releases \
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

        if any([l for l in self.untracked_files if path == l]):
            return True
        return False

    def uri(self):
        return exec_and_match(["git","remote","show","-n","origin"],
                              r'.*Fetch URL: (.*)',
                              cwd=self.path)

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
        
        print(str(self)+": add_dep("+str(name)+")")
        if self.get_dependency(name):
            log_error("Dependency already exists")
            return False

        dep = Dependency(parent=self)
        dep.repo_name = name
        if not os.path.isdir(dep.get_local_path()):
            log_error("Cannot add dependency '%s' as folder '%s' does not exist" % (name, dep.get_local_path()))
            return False

        print("creating Repo from " + str(dep.get_local_path())) 
        dep.repo = Repo_(dep.get_local_path())
        #print(str(dep.repo))
        dep.uri = dep.repo.uri()
        dep.githash = dep.repo.current_githash()

        # RSO
        dep.post_import()

        rel = dep.repo.current_release()
        if rel:
            dep.version_str = str(rel.version)

        self.dependencies.append(dep)
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
        temp_repo_path = os.path.join(path,os.path.basename(self.path))
        if git_only:
            (stdout_lines, stderr_lines) = call_get_output(
                    ["git", "clone", self.path], cwd=path)
            (stdout_lines, stderr_lines) = call_get_output(
                    ["git", "checkout", self.current_githash()], cwd=temp_repo_path)
        else:
            shutil.copytree(self.path, temp_repo_path)

        self._path = self.path
        self.path = os.path.join(path,self.name)
        self._prune_dirs()

    def orig_path(self):
        return self._path

    def move_to_temp_sandbox(self, git_only=True):
        dependencies = self.get_all_deps_once()
        self.sb = tempfile.mkdtemp()
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

    def get_module_version(self, module_name):
        repo_name = self.find_repo_containing_module(module_name)
        if not repo_name:
            log_error('%s: 1 Unable to find repo containing depedency %s' %
                (self.name, module_name))
            return None

        rel = None
        if repo_name == self.name:
            rel = self.latest_release()
        else:
            repo_dep = self.get_dependency(repo_name)
            if repo_dep and repo_dep.repo:
                rel = repo_dep.repo.latest_release()

        if rel:
            return rel.version.final_version_str()
        return None

    def get_module_repo(self, module_name, is_update):
        repo_name = self.find_repo_containing_module(module_name)

        print("get_module_repo(). Found: " + str(repo_name)) #FIXME

        if not repo_name:
            log_error('%s: 2 Unable to find repo containing depedency %s' %
                (self.name, module_name))
            return None

        if repo_name == self.name:
            return self
        else:
            repo_dep = self.get_dependency(repo_name)
           
            print("repo_dep: " + str(repo_dep))

            if repo_dep and repo_dep.repo:
                return repo_dep.repo

        print("get_module_repo() returning None")

        # Don't want this error message when this is an update that is going to fix it
        if not is_update:
            log_error('%s: 3 Unable to find repo containing depedency %s' %
                (self.name, module_name))

        return None

    def get_software_blocks(self, ignore_xsoftip_excludes=False, is_update=False):
        path = self.path
        components = []
        for x in os.listdir(path):
          if x == 'doc':
              continue
          if x in self.exclude_dirs:
              continue
          if x in self.docdirs:
              continue
          if not ignore_xsoftip_excludes and x in self.xsoftip_excludes:
              continue
          if x.startswith('__'):
              continue
          if self.is_untracked(x):
              continue
          mkfile = os.path.join(path,x,'Makefile')
          modinfo = os.path.join(path,x,'module_build_info')
          if os.path.exists(mkfile) or os.path.exists(modinfo) or x == 'module_xcommon' or (x in self.extra_eclipse_projects) or is_non_xmos_project(x, self) or re.match('^module_.*',x) or re.match('^lib_.*',x):
              comp = Component()
              comp.init_from_path(self, x)
              components.append(comp)
              comp.dependencies = get_project_immediate_deps(self, x, is_update=is_update)
              log_debug("Component %s has dependencies: %s" % (comp, comp.dependencies))

        return components

    def get_apps(self):
        return [x for x in self.get_software_blocks() if not x.is_module()]

    def get_modules(self):
        return [x for x in self.get_software_blocks() if x.is_module()]

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

      rel = self.get_release(version)
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

    def git_tag(self, version_string):
        v = Version(version_str=version_string)

        rel = self.get_release(v)

        relhash = self.get_child_hash(rel.parenthash)

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
                    with open(full_path, "wb") as f_ptr:
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

            try:
                v = Version(version_str=line.strip())
                if v in all_versions:
                    log_error("%s: Duplicate release note entries for %s" %
                        (self.name, fstr))
                all_versions.add(v)
            except VersionParseError:
                v = None

            if v:
                if current_version:
                    self.changelog_entries.append((str(current_version), items))
                current_version = v
                items = []
            else:
                items.append(line.rstrip())

        if current_version:
            self.changelog_entries.append((str(current_version), items))

    def find_repo_containing_module(self, module_name):
        root_dir = os.path.join(self.path, "..")

        #print("find_repo_containing_module: " + str(module_name))

        for dep_repo in os.listdir(root_dir):
            repo_path = os.path.join(root_dir, dep_repo)
            if os.path.isdir(repo_path):
                for module_dir in os.listdir(repo_path):
                    if os.path.isdir(os.path.join(repo_path, module_dir)):
                        if module_dir == module_name:
                            #print("found dir " + str(dep_repo))
                            return dep_repo
        #print("not found")
        return None

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
