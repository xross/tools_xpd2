from xmos_git_utils import get_repo, get_current_githash
from pathlib import Path
from xpd2.xpd_cmake import generate_cmake, Manifest_
from xpd2.xpd_version import Version
from xmos_logging import log_indent, log_unindent, log_error, log_warning, log_info, log_debug, configure_logging, print_status_summary
import os, re
from functools import total_ordering
import subprocess

@total_ordering
class Release:

    def __init__(self, version_str=None, path=None, virtual=False, notes = None):

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

    def parse_string(self, version_string):
        m = re.match(r'[vV]?(\d*)\.(\d*)\.(\d*)(alpha|beta|rc|)(\d*)_([-\w*])_(\d*)\.(\d*)\.(\d*)(alpha|beta|rc|)(\d*)', version_string)
        # what is this used for

        if m:
            on_branch = True
        else:
            on_branch = False
            m = re.search(r'[vV]?(\d*)\.(\d*)\.(\d*)(alpha|beta|rc|)(\d*)', version_string)
            if not m:
              m = re.match(r'(\d+)[vV](\d)(\d*)(alpha|beta|rc|)(\d*)', version_string)
              # do we want this
        if not m:
            raise Exception("VersionParseError")

        self.major   = 0         if m.group(1) == '' else int(m.group(1))
        self.minor   = 0         if m.group(2) == '' else int(m.group(2))
        self.point   = 0         if m.group(3) == '' else int(m.group(3))
        self.rtype   = "release" if m.group(4) == '' else     m.group(4)
        self.rnumber = 0         if m.group(5) == '' else int(m.group(5))

    @notes.setter
    def notes(self, n):
        self._notes = n

    def __lt__(self, other):
        return self.version < other.version

    def __eq__(self, other):
        return self.version == other.version

    def _find_hashes(self):

        # Return hash at tag and parent
        result = subprocess.run(["git", "rev-list", "-n", "1", "v"+str(self.version)], capture_output=True, universal_newlines=True)
        stdout_lines = result.stdout.splitlines()

        if stdout_lines:
            git_hash = stdout_lines[0].strip()

        result = subprocess.run(["git", "rev-parse", git_hash+"^"], capture_output=True, universal_newlines=True)
        stdout_lines0 = result.stdout.splitlines()

        if stdout_lines0:
            parent_hash = stdout_lines0[0].strip()
        else:
            parent_hash = None

        return (git_hash, parent_hash)

    def __str__(self):
        return "<release:" + str(self.version) + ">"

class Repo_():
    longname                = None #set by init
    path                    = None #set by init
    uri                     = None #set by init
    current_githash         = None #set by init
    current_release         = None
    required_release        = None
    latest_release          = None
    latest_prerelease       = None
    has_local_modifications = None
    current_branch          = None
    get_apps                = None
    _releases               = None
    repotype                = None #set by init

    def __init__(self, path: Path, manifest_item):
        self.path = path.resolve(strict=False)
        self.uri = get_repo(self.path)
        if self.uri is None:
            raise Exception(f"{self.path} is not a git repo")
        self.longname = list(filter(None, re.split(r'.*/|\.git',self.uri)))[0]
        self.current_githash = get_current_githash(self.path)
        self._set_repotype()

        if manifest_item is not None:
            self._versions_from_manifest(manifest_item)
        else:
            # TODO - assume if no manifest line then it's the top level and go explore for apps & examples to build for dependencies?
            pass

    def _set_repotype(self, repoType=None):
        if repoType is not None:
            self.repotype = repoType
        else:
            if(self.longname.startswith("sw_")):
                self.repotype = "app"
            elif(self.longname.startswith("lib_")):
                self.repotype = "lib"
            elif(self.longname.startswith("an")):
                self.repotype = "appnote"
            else:
                self.repotype = "unknown"

        self._releases  = self._find_releases()

    def _parse_manifest_item(self, manifest_item):
        self.longname = manifest_item.get('Name', None)
        self.uri = manifest_item.get('Location', None)
        self.current_githash = manifest_item.get('Changeset', None)
        self._verify_tag_and_set_current_release(manifest_item.get('Branch/tag', None), manifest_item.get('Dependency_requirement', None))

    def _versions_from_manifest(self, manifest_item):
        current_release =  manifest_item.get('Branch/tag', None)
        required_release = manifest_item.get('Dependency_requirement', None)
        try:
            self.current_release = Version(version_str=current_release)
        except:
            log_warning(f"{self.longname} not on a release tag {current_release}")
            self.current_release = current_release
        try:
            self.required_release = Version(version_str=required_release)
        except:
            log_error(f"{self.longname} required release tag format error {required_release}")
            self.required_release = required_release
        if current_release != required_release:
            log_warning(f"{self.longname} Current tag is {self.current_release}, requires {self.required_release}")

    def _Tag(self):
        pass

    def _verify_tag_and_set_current_release(self, detected_tag, required_tag):
        if None in [detected_tag, required_tag]:
            log_error(f"Manifest pase error, unable to read Branch/tag: {detected_tag} or Dependency_requirement: {required_tag}")
        elif detected_tag == required_tag:
            if detected_tag.startswith('v'):
                detected_tag = detected_tag[1:]
            self.current_release = Version(version_str=detected_tag)
        else:
            log_warning(f"{self.longname} Current tag is {self.current_release}, requires {self.required_release}")

    def _parse_changelog(self):
        pass
    def _check_changelog(self):
        pass
    def _check_readme(self):
        pass
    def _check_licence(self):
        pass

    @property
    def releases(self):
        rels = self._releases
        rels.sort()
        rels.reverse()
        return rels

    def _find_releases(self):

        releases = []

        result = subprocess.run(["git", "tag", "--merged", "remotes/origin/master", "-l", "v*"], capture_output=True, universal_newlines=True)
        stdout = result.stdout.splitlines()

        for line in stdout:
            line = str(line).replace('v','').replace('\n','')

            try:
                release = Release(version_str=line, path=self.path)
                releases.append(release)
            except VersionParseError:
                log_warning(f'Bad version in tag: {str(line)}')

        return releases

    def print(self):
        log_info(f"           Name : {self.longname}")
        log_info(f"           Path : {self.path}")
        log_info(f"       Location : {self.uri}")
        log_info(f"        Version : {self.current_githash}")
        log_info(f"        Release : {self.current_release}")

class Sandbox_(Repo_):
    _deps                    = []
    def __init__(self, path: Path):
        generate_cmake(path)
        manifest = Manifest_(path / 'build' / 'manifest.txt')
        if not manifest.exists():
            #TODO - error handeling (this is another check that the manifest exists, probably not required)
            log_error("Manifest not found")
            pass
        else:
            manifest_items = manifest.items()
            sandbox = manifest_items[0]
            deps = manifest_items[1:]
            for dep in deps:
                dep_path = path.parent / dep['Name'] #TODO - make this safer
                self._deps.append(Repo_(dep_path,dep))
            super().__init__(path, sandbox)

    # TODO - modify the _verify_tag_and_set_current_release function for sandbox to allow
    #        the user to increment / update version number for release

    def print(self):
        log_info("INFO:\n")
        super().print()
        log_info("   Dependencies :")
        log_indent()
        for dep in self._deps:
            dep.print()
            log_info("\n")
        log_unindent()

    def _check_tag(self):
        return True

#configure_logging()
#manifest_location = Path(os.getcwd())
#generate_cmake(manifest_location)
#manifest = Manifest_(manifest_location / 'build' / 'manifest.txt')
#manifest_items = manifest.items()
#for item in manifest_items:
#    item_path = manifest_location.parent / item['Name']
#    repo = Repo_(item_path, item)
#    repo.print()
# sandbox = Sandbox_(manifest_location)
# sandbox.print()
