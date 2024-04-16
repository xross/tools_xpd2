from pathlib import Path
from xmos_logging import log_error, log_warning, log_info, log_debug, configure_logging, print_status_summary
import subprocess

def generate_cmake(path: Path):
    CMakeLists = path / 'CMakeLists.txt'
    if not CMakeLists.exists():
        log_error(f"{CMakeLists.absolute} not found.")
    else:
        cmd = ['cmake', '-G', 'Unix Makefiles', '-B', 'build', '-D', 'FULL_MANIFEST=TRUE']
        with open('xpd.log', 'w') as logfile:
            subprocess.call(cmd, stdout=logfile)

class Manifest_:
    _exists = False
    _lines = []
    def __init__(self, path: Path):
        self._exists = path.exists()
        if self.exists():
            with open(path) as f:
                lines = f.read().split('\n')
                columns = " ".join(lines[0].split('|')).split()
                for line in lines[2:-1]:
                    line = " ".join(line.split('|')).split()
                    if len(columns) != len(line):
                        log_error(f"Mismatch of column headings\n{columns}\nand column data\n{line}\nin manifest file")
                        pass
                    else:
                        self._lines.append({columns[i]: line[i] for i in range(len(columns))})
        else:
            log_error(f"Manifest not found at {path}")

    def print(self):
        for i, line in enumerate(self._lines):
            padding = max(len(key) for key in line.keys())
            if i != 0:
                log_info(f"{f'Dep[{i}]':{' '}{'>'}{padding}} :")
                padding += padding + 3
            for key, value in line.items():
                log_info(f"{key:{' '}{'>'}{padding}} : {value}")

    def exists(self):
        return self._exists
    
    def validate(self):
        #TODO - validate the branch/tag once supported by the manifest file
        return True
    
    def items(self):
        return self._lines
    