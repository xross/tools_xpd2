from xmos_git_utils import get_repo, get_current_githash
from pathlib import Path
from xpd2.xpd_cmake import generate_manifest, Manifest
from xpd2.xpd_version import Version, VersionParseError
from xmos_logging import (
    log_indent,
    log_unindent,
    log_error,
    log_warning,
    log_info,
    log_debug,
    configure_logging,
    print_status_summary,
)
import os, re
from functools import total_ordering
import subprocess

MAIN_BRANCH_NAMES = ["master", "main"]


def exec_and_match(command, regexp, cwd=None):

    result = subprocess.run(
        command, capture_output=True, universal_newlines=True, cwd=cwd
    )
    stdout_lines = result.stdout.splitlines()

    for line in stdout_lines:
        m = re.match(regexp, line)
        if m:
            return m.groups(0)[0]
    return None


def call_get_output(command, cwd=None):
    result = subprocess.run(
        command, capture_output=True, universal_newlines=True, cwd=cwd
    )
    stdout_lines = result.stdout.splitlines()
    stderr_lines = result.stderr.splitlines()
    return (stdout_lines, stderr_lines)

def call(command, cwd=None, silent=False):
    if silent:
        result = subprocess.run(command, cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        result = subprocess.run(command, cwd=cwd, check=True)
    return not result

@total_ordering
class Release:

    def __init__(self, version_str=None, path=None, virtual=False, notes=None):

        self.parenthash = None
        self.githash = None
        self.virtual = virtual
        self.path = path
        self.version = None
        self._notes = notes

        if version_str:
            try:
                self.version = Version(version_str=version_str)
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

    def __lt__(self, other):
        return self.version < other.version

    def __eq__(self, other):
        return self.version == other.version

    def _find_hashes(self):

        # Return hash at tag and parent
        result = subprocess.run(
            ["git", "rev-list", "-n", "1", "v" + str(self.version)],
            capture_output=True,
            universal_newlines=True,
            cwd=self.path,
        )
        stdout_lines = result.stdout.splitlines()

        if stdout_lines:
            git_hash = stdout_lines[0].strip()

        result = subprocess.run(
            ["git", "rev-parse", git_hash + "^"],
            capture_output=True,
            universal_newlines=True,
            cwd=self.path,
        )
        stdout_lines0 = result.stdout.splitlines()

        if stdout_lines0:
            parent_hash = stdout_lines0[0].strip()
        else:
            parent_hash = None

        return (git_hash, parent_hash)

    def __str__(self):
        return "<release:" + str(self.version) + ">"

class Repo:
    name = None  # set by init
    path = None  # set by init
    uri = None  # set by init
    _latest_release = None
    _latest_pre_release = None
    _latest_full_release = None
    _local_modifications = None
    current_branch = None
    get_apps = None
    _releases = None
    repotype = None  # set by init
    #required_version = None  # The version as required by the manifest (could be a release, githash or -)
    current_release = (
        None  # The current release version of the repo (None if not a release)
    )
    current_githash = None  # The githash of that the repo is currently at
    _behind_upstream = None
    changelog_entries = None

    def __init__(self, path: Path, manifest_item):

        self.dependencies = []

        self.path = path.resolve(strict=False)
        self.name = manifest_item["Name"]
        self.uri = manifest_item["Location"]
        self.current_githash = manifest_item["Changeset"]
        self._set_repotype()

        self._releases = self._find_releases()
        self.current_release = self._get_current_release()

        for dep_str in manifest_item["Depends_on"].split(","):
            match = re.search(r'(\w+)\(([\w.]+)\)', dep_str)
            dep_version = None
            if match:
                dep_name = match.group(1)
                if match.group(2):
                    dep_version_str = match.group(2)

                try:
                    dep_version = Version(version_str=dep_version_str)
                    self.dependencies.append(Dependency(dep_name, version=Version(version_str=dep_version_str)))
                except VersionParseError:
                    log_info(f"{dep_name} has no specified version ({dep_version_str})")
                    self.dependencies.append(Dependency(dep_name, branch=dep_version_str))

        self._git_fetch()

        self.parse_changelog()

    # TODO use shared code from infr_apps/infr_scripts_py
    def parse_changelog(self):
        ''' Parse the changelog file and convert it to a map list of (version, items) entries.
            Also checks that there are no duplicate entries for the same version number
            and that the order of versions in the CHANGELOG is correct.
        '''
        self.changelog_entries = []
        rst_title_regexp = r'[-=^~#.][-=^~#.]+'

        changelog_path = os.path.join(self.path, 'CHANGELOG.rst')
        if not os.path.exists(changelog_path):
            log_warning(f"Cannot find CHANGELOG.rst in {self.name}")
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
            releases = self.get_releases_for_version(version)
            for r in releases:
                r.notes = notes

    def get_versioned_repo(self, version):
        rel = self.get_release(version)
        if not rel or not rel.parenthash:
            return None

    @property
    def behind_upstream(self):

        if self._behind_upstream != None:
            return self._behind_upstream

        self._behind_upstream = False
        (stdout_lines, stderr_lines) = call_get_output(["git", "status", "-uno"], cwd=self.path)

        for line in stdout_lines:
            if re.match('.*is behind*', line):
                self._behind_upstream = True
            if re.match('.*diverged*', line):
                self._behind_upstream = True

        return self._behind_upstream

    def _git_fetch(self):
        retval = call(["git", "fetch"], cwd=self.path, silent=True)
        if retval:
          log_error(f"{self.name}: failed to fetch")

    def _set_repotype(self, repoType=None):
        if repoType is not None:
            self.repotype = repoType
        else:
            if self.name.startswith("sw_"):
                self.repotype = "app"
            elif self.name.startswith("lib_"):
                self.repotype = "lib"
            elif self.name.startswith("an"):
                self.repotype = "appnote"
            else:
                self.repotype = "unknown"

    def _versions_from_manifest(self, manifest_item):
        current_release = manifest_item.get("Branch/tag", None)
        try:
            self.current_release = Version(version_str=current_release)
        except:
            log_warning(f"{self.name} not on a release tag {current_release}")
            self.current_release = current_release

    @property
    def version(self):
        if self.current_release:
            return self.current_release.version
        return None

    def _Tag(self):
        pass

    def _verify_tag_and_set_current_release(self, detected_tag, required_tag):
        if None in [detected_tag, required_tag]:
            log_error(
                f"Manifest pase error, unable to read Branch/tag: {detected_tag} or Dependency_requirement: {required_tag}"
            )
        elif detected_tag == required_tag:
            if detected_tag.startswith("v"):
                detected_tag = detected_tag[1:]
            self.current_version = Version(version_str=detected_tag)
        else:
            log_warning(
                f"{self.name} Current tag is {self.current_release}, requires {self.required_release}"
            )

    def _parse_changelog(self):
        pass

    def _check_changelog(self):
        pass

    def _check_readme(self):
        pass

    def _check_licence(self):
        pass

    def get_release(self, version):
        found = None
        for r in self._releases:
            if r.version == version:
                found = r
        return found

    # Returns all releases matching a certain verison (we could have 1.0.0alpha and 1.0.0beta for example)
    def get_releases_for_version(self, version):
        releases = []
        for r in self.releases:
            if r.version == version:
                releases.append(r)
        return releases

    # Latest release (release object)
    @property
    def latest_release(self):
        if self._latest_release == None:
            releases = self.releases
            releases.sort()
            if releases:
                self._latest_release = releases[-1]
        return self._latest_release

    # Latest release that matches a filter
    def latest_release_filtered(self, filter=None):
        if filter:
            rels = [r for r in self._releases if filter(r)]
        else:
            rels = self._releases
        rels.sort()
        if rels != []:
            return rels[-1]
        return None

    # Latest release that isn't alpha/beta..(release object)
    @property
    def latest_full_release(self):
        if self._latest_full_release:
            return self._latest_full_release

        self._latest_full_release = self.latest_release_filtered(filter=lambda r: r.version.is_full())
        return self._latest_full_release

     # Latest pre-release i.e. alpha, beta (release object)
    @property
    def latest_pre_release(self):
        if self._latest_pre_release:
            return self._latest_pre_release

        self._latest_pre_release = self.latest_release_filtered(filter=lambda r: not r.version.is_full() and not r.version.branch_name)

        return self._latest_pre_release

    @property
    def releases(self):
        rels = self._releases
        rels.sort()
        rels.reverse()
        return rels

    def _find_releases(self):
        releases = []
        stdout = ""
        #for branch in MAIN_BRANCH_NAMES:
        result = subprocess.run(
            #["git", "tag", "--merged", f"remotes/origin/{branch}", "-l", "v*"],
            # For the moment check all branches
            ["git", "tag", "-l", "v*"],
            capture_output=True,
            universal_newlines=True,
            cwd=self.path,
            )
        stdout = stdout + result.stdout

        stdout = stdout.splitlines()

        for line in stdout:
            line = str(line).replace("v", "").replace("\n", "")

            try:
                release = Release(version_str=line, path=self.path)
                releases.append(release)
            except VersionParseError:
                log_warning(f"Bad version in tag: {str(line)}")

        return releases

    def _get_current_release(self):

        if not self.path:
            return None

        parent_hash = exec_and_match(
            ["git", "rev-parse", "HEAD~1"], r"(.*)", cwd=self.path
        )

        rels = []
        for release in self._releases:
            if hasattr(release, "parenthash") and parent_hash == release.parenthash:
                rels.append(release)

        rels.sort()

        if rels != []:
            return rels[-1]

        return None

    def current_version_or_githash(self, short=False):
        rel = self.current_release
        if rel:
            vstr = str(rel.version)
        else:
            if short:
                vstr = self.current_githash[:8]
            else:
                vstr = self.current_githash
        return vstr

    @property
    def has_local_modifications(self):
        mods = self.local_modifications(refresh = False)
        if mods:
            return True
        return False

    def local_modifications(self, refresh = False):
        if (self._local_modifications == None) or refresh:
            self._local_modifications = self._get_local_modifications()
        return self._local_modifications

    def _get_local_modifications(self, is_dependency=False, unstaged_only=False):
        (stdout_lines, stderr_lines) = call_get_output(
            ["git", "update-index", "-q", "--refresh"], cwd=self.path
        )

        if unstaged_only:
            (stdout_lines, stderr_lines) = call_get_output(
                ["git", "diff", "--name-only"], cwd=self.path
            )
        else:
            (stdout_lines, stderr_lines) = call_get_output(
                ["git", "diff-index", "--name-only", "HEAD", "--"], cwd=self.path
            )

        # Ignore files which are changed by xpd unless it is a dependent repo which must have no changes
        if not is_dependency:
            stdout_lines = [
                x.rstrip()
                for x in stdout_lines
                if not re.search("(^fatal:|\.xproject|\.cproject|\.project|xpd.xml)", x)
            ]

        return stdout_lines

    def print(self):
        log_info(f"            Name : {self.name}")
        log_info(f"            Path : {self.path}")
        log_info(f"        Location : {self.uri}")
        #log_info(f"Required Version : {self.required_version}")
        local_mod = ""
        if self.has_local_modifications:
            local_mod = "(local modifications)"
        log_info(
            f"  Actual Version : {self.current_release_or_githash()} {local_mod}"
        )
        log_info(f"     Dependencies:")
        for d in self.dependencies:
            log_info(f"                   {d.name} ({d.version})")

    def __str__(self):
        return "<repo:" + str(self.name) + ">"

class Dependency():

    def __init__(self, name, version=None, branch=None, parent_repo=None, repo=None):
        self._version = version
        self._parent_repo = parent_repo
        self._repo = repo
        self.name = name
        self.branch = branch

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
        return self._repo.current_githash

    @property
    def repo_name(self):
        return self._repo.name

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, v):
        self._version = v

    def get_local_path(self):
        root_repo = self.parent
        return os.path.join(os.path.join(root_repo.path,".."),self.repo_name)

    def __str__(self):
        return f"<Dependency: {self.name}({self.version})>"

class Sandbox:
    _repos = []

    def __init__(self, path: Path):
        # order of operations
        # - check this is being run on a git repo
        # - get the name of the top level repo form the uri
        # - infer the type of repo from the name
        # - run cmake in an appropriate way to generate a manifest
        uri = get_repo(path.resolve(strict=False))
        name = list(filter(None, re.split(r'.*/|\.git',uri)))[0]
        if name.startswith("sw_"):
            repotype = "app"
        elif name.startswith("lib_"):
            repotype = "lib"
        elif name.startswith("an"):
            repotype = "appnote"

        def build_deps(repo):
            pass

        manifest_path = generate_manifest(path, repotype)
        manifest = Manifest(manifest_path)

        for item in manifest.contents:
            repo_path = path.parent / item["Name"]
            self._repos.append(Repo(repo_path, item))

        #Build up dependency tree
        #print("DEP_TREE")
        #for repo in self._repos:
        #    print(f"{repo.name}")
        #    for dep in repo.dependencies:
        #        print(f"{dep}")

    @property
    def repos(self):
        return self._repos

    def find_repo_by_name(self, repo_name):
        for r in self._repos:
            if r.name == repo_name:
                return r
        return None

    def get_all_repos_using_dep(self, dep):
        repos = []
        for r in self._repos:
            for d in r.dependencies:
                if d == dep:
                    repos.append(r)
        return repos

    def print(self):
        log_indent()
        for repo in self._repos:
            repo.print()
            log_info("\n")
        log_unindent()

    def _check_tag(self):
        return True

