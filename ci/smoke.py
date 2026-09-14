"""Exercise the package's own binary; no network, no model, no oracle."""
from pathlib import Path
import subprocess, tempfile

BIN = Path(__file__).resolve().parents[1] / "gramide_python"

def run(*args, code=0):
    p = subprocess.run([str(BIN), *map(str, args)], capture_output=True, text=True, timeout=30)
    assert p.returncode == code, (args, p.returncode, p.stdout, p.stderr)
    return p.stdout

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for ext in ["py", "pyi"]:
        source = root / ("valid." + ext)
        source.write_text("class Box:\n    def read(self) -> int: ...\n")
        run("check", source)
        assert "Box.read" in run("outline", source)
        broken = root / ("broken." + ext)
        broken.write_text("class Box:\n    def read(self) -> int: ...\n)\n")
        run("check", broken, code=1)
    assert run("version").splitlines()[0].startswith("gramide_python ")
print("CLI smoke passed: .py and .pyi outlines and syntax rejection")
