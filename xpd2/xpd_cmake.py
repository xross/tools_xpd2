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


def generate_manifest(path: Path, repotype: str):
    CMakeLists_location = path
    match repotype:
        case "app":
            # check for top level CMakeLists
            if not Path.exists(CMakeLists_location / "CMakeLists.txt"):
                raise Exception(f"{repotype} repo {path} requires CMakeLists.txt in top level")
        case "lib":
            examples_dir = path / "examples"
            # see if there is a combined cmake for the examples
            if Path.exists(examples_dir / "CMakeLists.txt"):
                CMakeLists_location = examples_dir
            else:
                # if there's no CMakeLists.txt for all the examples look for one in the folders.
                for example in examples_dir.iterdir():
                    if example.is_dir() and Path.exists(example / "CMakeLists.txt"):
                        CMakeLists_location = example
                        break
            if not Path.exists(CMakeLists_location / "CMakeLists.txt"):
                raise Exception("No examples are setup for use with cmake")
        case "appnote":
            raise Exception("appnote release process not yet supported")
        case _:
            raise Exception(f"repotype {repotype} not supported")

    cmd = [
        "cmake",
        "-S",
        CMakeLists_location,
        "-G",
        "Unix Makefiles",
        "-B",
        CMakeLists_location / "build",
        "-D",
        "FULL_MANIFEST=TRUE",
    ]

    #TODO we miss stderr here
    with open("xpd.log", "w") as logfile:
        subprocess.call(cmd, stdout=logfile)
    manifest_path = Path(CMakeLists_location / "build" / "manifest.txt")
    if manifest_path.exists():
        return manifest_path
    else:
        return None


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
