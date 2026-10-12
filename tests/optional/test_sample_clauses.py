import re
from pathlib import Path


def test_clause_sample_defaults_to_an_ignored_folder():
    import subprocess
    import sample_clauses as SC
    import inspect
    default = re.search(r'"--out", default="([^"]+)"', inspect.getsource(SC)).group(1)
    root = Path(__file__).resolve().parents[2]
    assert subprocess.run(["git", "check-ignore", "-q", default], cwd=root).returncode == 0, default
