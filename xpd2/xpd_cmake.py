from pathlib import Path
import logging
import subprocess

def generate_cmake(path: Path):
    CMakeLists = path / 'CMakeLists.txt'
    if not CMakeLists.exists():
        logging.error(f"{CMakeLists.absolute} not found.")
    else:
        cmd = ['cmake', '-G', 'Unix Makefiles', '-B', 'build']
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
                for line in lines[2:]:
                    line = " ".join(line.split('|')).split()
                    if len(columns) != len(line):
                        #TODO - error handling (more data than column headings)
                        pass
                    else:
                        self._lines.append({columns[i]: line[i] for i in range(len(columns))})
        else:
            #TODO - Error handling (missing manifest file)
            pass

    def print(self):
        for i, line in enumerate(self._lines):
            padding = max(len(key) for key in line.keys())
            if i != 0:
                print(f"{f'Dep[{i}]':{' '}{'>'}{padding}} :")
                padding += padding + 3
            for key, value in line.items():
                print(f"{key:{' '}{'>'}{padding}} : {value}")

    def exists(self):
        return self._exists
    
    def validate(self):
        #TODO - validate the branch/tag once supported by the manifest file
        return True
    
    def items(self):
        return self._lines
    