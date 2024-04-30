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

    # @notes.setter
    # def notes(self, n):
    #    self._notes = n

    @property
    def notes(self):
        return self._notes

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
    latest_prerelease = None
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
                    dep_version = match.group(2)
                self.dependencies.append(Dependency(dep_name, dep_version))

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

    # def _parse_manifest_item(self, manifest_item):
    #    self.name = manifest_item.get('Name', None)
    #    self.uri = manifest_item.get('Location', None)
    #    self.current_githash = manifest_item.get('Changeset', None)
    #    self._verify_tag_and_set_current_release(manifest_item.get('Branch/tag', None), manifest_item.get('Dependency_requirement', None))

    def _versions_from_manifest(self, manifest_item):
        current_release = manifest_item.get("Branch/tag", None)
        #required_release = manifest_item.get("Dependency_requirement", None)
        try:
            self.current_release = Version(version_str=current_release)
        except:
            log_warning(f"{self.name} not on a release tag {current_release}")
            self.current_release = current_release
        #try:
        #    self.required_release = Version(version_str=required_release)
        #except:
        #    log_error(
        #        f"{self.name} required release tag format error {required_release}"
        #    )
        #    self.required_release = required_release
        #if current_release != required_release:
        #    log_warning(
        #        f"{self.name} Current tag is {self.current_release}, requires {self.required_release}"
        #    )

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

    @property
    def latest_release(self):
        if self._latest_release == None:
            releases = self.releases
            releases.sort()
            if releases:
                self._latest_release = releases[-1]
        return self._latest_release

    @property
    def releases(self):
        rels = self._releases
        rels.sort()
        rels.reverse()
        return rels

    def _find_releases(self):
        releases = []
        stdout = ""
        for branch in MAIN_BRANCH_NAMES:
            result = subprocess.run(
                ["git", "tag", "--merged", f"remotes/origin/{branch}", "-l", "v*"],
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

    def current_release_or_githash(self, short=False):
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
        if self.local_modifications:
            return True
        return False

    @property
    def local_modifications(self):
        if self._local_modifications == None:
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

    def __init__(self, name, version, parent_repo=None, repo=None, ):
        self._version = None
        self._parent_repo = parent_repo
        self._repo = repo
        self.name = name
        self.version = version

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

        # Build up dependency tree
        for repo in self._repos:
            print(f"{repo.name}")
            for dep in repo.dependencies:
                print(f"{dep}")




    # TODO - modify the _verify_tag_and_set_current_release function for sandbox to allow
    #        the user to increment / update version number for release

    def print(self):
        log_indent()
        for repo in self._repos:
            repo.print()
            log_info("\n")
        log_unindent()

    def _check_tag(self):
        return True

