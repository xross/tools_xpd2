from pathlib import Path
from xpd_cmake import generate_cmake, Manifest_
from xmos_logging import log_indent, log_unindent, log_error, log_warning, log_info, log_debug, configure_logging, print_status_summary
import os, re
from functools import total_ordering

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
            log_error("Version parse error")
            # raise VersionParseError

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
        self._verify_tag_and_set_current_release(manifest_item.get('Branch/tag', None), manifest_item.get('Dependency_requirement', None))

        if None in [
            self.longname,
            self.uri,
            self.current_githash,
            ]:
            # TODO - maybe this should rase an exception? 
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
            log_error(f"{self.longname} Current tag is {self.current_release}, requires {self.required_release}")

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

configure_logging()
manifest_location = Path(os.getcwd())

sandbox = Sandbox_(manifest_location)
sandbox.print()
