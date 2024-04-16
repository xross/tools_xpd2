from pathlib import Path
from xpd_cmake import generate_cmake, Manifest_
from xmos_logging import log_indent, log_unindent, log_error, log_warning, log_info, log_debug, configure_logging, print_status_summary
import os

class Repo_():
    longname                = None
    path                    = None
    uri                     = None
    current_githash         = None
    current_release         = None
    latest_release          = None
    latest_prerelease       = None
    has_local_modifications = None
    current_branch          = None
    get_apps                = None
    releases                = None

    def __init__(self, path: Path, manifest_item: dict | None = None):
        self.path = path.resolve(strict=False)
        if manifest_item is not None:
            self._parse_manifest_item(manifest_item)
        self._parse_changelog()

    def _parse_manifest_item(self, manifest_item):
        self.longname = manifest_item.get('Name', None)
        self.uri = manifest_item.get('Location', None)
        self.current_githash = manifest_item.get('Changeset', None)
        self.current_release = manifest_item.get('Branch/tag', None)
        if None in [
            self.longname,
            self.uri,
            self.current_githash,
            self.current_release,
            ]:
            #TODO Error handling (manifest column headings differ from expected)
            pass


    def _Tag(self):
        pass
    def _parse_changelog(self):
        pass
    def _check_changelog(self):
        pass
    def _check_readme(self):
        pass
    def _check_licence(self):
        pass

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
            super().__init__(path, sandbox)
            for dep in deps:
                dep_path = path.parent / dep['Name'] #TODO - make this safer
                self._deps.append(Repo_(dep_path,dep))

    def print(self):
        log_info("INFO:\n")
        super().print()
        log_info("   Dependencies :")
        log_indent()
        for dep in self._deps:
            dep.print()
            log_info("\n")
        log_unindent()


configure_logging()
manifest_location = Path(os.getcwd())

sandbox = Sandbox_(manifest_location)
sandbox.print()
