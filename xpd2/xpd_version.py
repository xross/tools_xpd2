
from functools import total_ordering
import os, re

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

