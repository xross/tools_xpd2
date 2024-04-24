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
    longname                = None
    path                    = None
    uri                     = None
    current_githash         = None
    current_release         = None
    required_release        = None
    latest_release          = None
    latest_prerelease       = None
    has_local_modifications = None
    current_branch          = None
    get_apps                = None
    _releases               = None
    repotype                = None

    def __init__(self, path: Path, manifest_item):
        self.path = path.resolve(strict=False)
        if manifest_item is not None:
            self._parse_manifest_item(manifest_item)
        self._parse_changelog()

        if(self.longname.startswith("sw_")):
            self.repotype = "app"
        elif(self.longname.startswith("lib_")):
            self.repotype = "lib"
        elif(self.longname.startswith("an")):
            self.repotype = "appnote"

        self._releases  = self._find_releases()

    def _parse_manifest_item(self, manifest_item):
        self.longname = manifest_item.get('Name', None)
        self.uri = manifest_item.get('Location', None)
        self.current_githash = manifest_item.get('Changeset', None)
        self._verify_tag_and_set_current_release(manifest_item.get('Branch/tag', None), manifest_item.get('Dependency_requirement', None))

        if None in [
            self.longname,
            self.uri,
            self.current_githash,
            ]:
            # TODO - maybe this should raise an exception?
            log_error("Manifest.txt headings don't match expected.")

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

#sandbox = Sandbox_(manifest_location)
#sandbox.print()
