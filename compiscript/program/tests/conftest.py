import re
import subprocess
from pathlib import Path

PROG_DIR = Path(__file__).resolve().parents[1]
DRIVER = PROG_DIR / "Driver.py"
TAC_TXT = PROG_DIR / "tac.txt"

def run_compiler(source: str, name: str = "tmp.cps", extra_args=("--tac", "--mips")):
 
    src_path = PROG_DIR / name
    src_path.write_text(source)
    # ejecuta el compilador
    cp = subprocess.run(
        ["python", str(DRIVER), str(src_path.name), *extra_args],
        cwd=PROG_DIR,
        text=True,
        capture_output=True
    )
    tac = TAC_TXT.read_text() if TAC_TXT.exists() else ""
    return cp.stdout, cp.stderr, tac, cp.returncode

TEMP_RE = re.compile(r"\bt(\d+)\b")
LABEL_RES = [
    re.compile(r"\bL\d+\b"),         
    re.compile(r"\bL\d+:\b"),        
    re.compile(r"\bLabel\b", re.I),
]

def temp_set(tac: str):
    return set(TEMP_RE.findall(tac))

def has_labels(tac: str) -> bool:
    return any(r.search(tac) for r in LABEL_RES)
