import re
from pathlib import Path


RE_EXPORT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")


def parse_rc_file(path: Path):
    env = {}
    if not path.exists():
        raise FileNotFoundError("RC file not found: %s" % path)
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("echo ") or line.startswith("read "):
            continue
        if line.startswith("[[ ") and "]]" in line:
            continue
        m = RE_EXPORT.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        env[key] = value
    return env


def build_rc_path(repo_root: Path, profile: str, catalog: str, override):
    if override:
        p = Path(override)
        return p if p.is_absolute() else (repo_root / p)
    return repo_root / profile / ("rc-%s.sh" % catalog)

