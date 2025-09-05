import json
import os
from pathlib import Path
from typing import Dict, Tuple
import base64


def config_path() -> Path:
    xdg = os.getenv("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "ossc" / "profiles.json"
    # POSIX default
    return Path.home() / ".config" / "ossc" / "profiles.json"


def load_profiles_config(repo_root: Path) -> Tuple[Dict, Path, bool]:
    cfg_path = config_path()
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8")), cfg_path, False
        except Exception:
            pass
    return {}, cfg_path, False


def _deep_update(dst: Dict, src: Dict):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = v


def save_profiles_config(cfg_path: Path, profiles: Dict):
    cfg_dir = cfg_path.parent
    cfg_dir.mkdir(parents=True, exist_ok=True)
    # Merge with existing on disk to avoid overwriting other profiles/catalogs
    merged = {}
    if cfg_path.exists():
        try:
            existing = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                merged = existing
        except Exception:
            merged = {}
    if isinstance(merged, dict):
        _deep_update(merged, profiles)
    else:
        merged = profiles
    cfg_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(cfg_path, 0o600)
    except Exception:
        pass


def ensure_profiles_structure(cfg: Dict) -> Dict:
    if "profiles" not in cfg:
        migrated = {"profiles": {}}
        for k, v in cfg.items():
            if isinstance(v, dict):
                entry = dict(v)
                entry.setdefault("catalogs", {})
                migrated["profiles"][k] = entry
        cfg = migrated
    else:
        for _, pdata in list(cfg.get("profiles", {}).items()):
            pdata.setdefault("catalogs", {})
    return cfg


def get_catalog_env(config: Dict, profile: str, catalog: str):
    cfg = ensure_profiles_structure(dict(config))
    pdata = cfg.get("profiles", {}).get(profile)
    if not pdata:
        return None
    cat = pdata.get("catalogs", {}).get(catalog)
    if not cat:
        return None
    return dict(cat)


def resolve_password(args, profile_entry: Dict, rc_env: Dict = None):
    # Highest priority: explicit flag
    if getattr(args, "password", None):
        return args.password
    # Env vars (allow both project-specific and OS_* for convenience)
    if os.getenv("OSS_PASSWORD"):
        return os.getenv("OSS_PASSWORD")
    if os.getenv("OS_PASSWORD"):
        return os.getenv("OS_PASSWORD")
    # Stored plain password in profile
    if (profile_entry or {}).get("password"):
        return profile_entry.get("password")
    # Stored as base64 in profile (optional)
    b64 = (profile_entry or {}).get("password_b64")
    if b64:
        try:
            return base64.b64decode(b64).decode("utf-8")
        except Exception:
            pass
    # From RC/config catalog environment
    if (rc_env or {}).get("OS_PASSWORD"):
        return rc_env.get("OS_PASSWORD")
    return None


def resolve_username(args, profile_entry: Dict, rc_env: Dict):
    if getattr(args, "username", None):
        return args.username
    if os.getenv("OSS_USERNAME"):
        return os.getenv("OSS_USERNAME")
    if (profile_entry or {}).get("username"):
        return profile_entry.get("username")
    return (rc_env or {}).get("OS_USERNAME")
