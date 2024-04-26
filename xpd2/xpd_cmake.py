from pathlib import Path
from xmos_logging import (
    log_error,
    log_warning,
    log_info,
    log_debug,
    configure_logging,
    print_status_summary,
)
import subprocess
import re


def generate_manifest(path: Path):
    CMakeLists = path / "CMakeLists.txt"
    if not CMakeLists.exists():
        log_error(f"{CMakeLists.absolute} not found.")
    else:
        cmd = [
            "cmake",
            "-G",
            "Unix Makefiles",
            "-B",
            "build",
            "-D",
            "FULL_MANIFEST=TRUE",
        ]
        with open("xpd.log", "w") as logfile:
            subprocess.call(cmd, stdout=logfile)


class Manifest:
    _exists = False
    _lines = []
    _contents = []

    def __init__(self, path: Path):
        self._exists = path.exists()
        if self.exists():
            with open(path) as file:

                # Skip the header lines
                next(file)
                next(file)

                for line in file:

                    fields = re.split(f"\s+", line.strip())

                    row = {
                        "Name": fields[0].strip(),
                        "Location": fields[1].strip(),
                        "Branch/tag": fields[2].strip(),
                        "Changeset": fields[3].strip(),
                        "Dependency_requirement": fields[4].strip(),
                        "Depends_on": (
                            " ".join(fields[5:]).strip() if len(fields) > 5 else ""
                        ),
                    }
                    self._contents.append(row)
        else:
            log_error(f"Manifest not found at {path}")

    def print(self):
        for row in self._contents:
            print("Name:                ", row["Name"])
            print("Location:            ", row["Location"])
            print("Branch/tag:          ", row["Branch/tag"])
            print("Changeset:           ", row["Changeset"])
            print("Dependency_requirement:", row["Dependency_requirement"])
            print("Depends_on:          ", row["Depends_on"])
            print("-" * 60)

    @property
    def contents(self):
        return self._contents

    def exists(self):
        return self._exists

    def validate(self):
        # TODO - validate the branch/tag once supported by the manifest file
        return True

    def items(self):
        return self._lines
