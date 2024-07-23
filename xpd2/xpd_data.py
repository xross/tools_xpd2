from pathlib import Path
from xpd2.xpd_version import VersionParseError
from build_system.repository import Version
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

    def _versions_from_manifest(self, manifest_item):
        current_release = manifest_item.get("Branch/tag", None)
        try:
            self.current_release = Version(version_str=current_release)
        except:
            log_warning(f"{self.name} not on a release tag {current_release}")
            self.current_release = current_release


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
