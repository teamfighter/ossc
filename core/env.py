import os
import shutil
import subprocess
from pathlib import Path


def user_venv_paths():
    xdg = os.getenv("XDG_DATA_HOME") or os.getenv("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else (Path.home() / ".config")
    # Only OSSC path (no legacy fallbacks), POSIX-only
    return [base / "ossc" / "venv"]


def venv_bin_dir(venv_path: Path) -> Path:
    return venv_path / "bin"


def ensure_openstack_available(repo_root: Path, env: dict):
    exe = shutil.which("openstack", path=env.get("PATH")) or shutil.which("openstack")
    if exe:
        return env, exe

    local_venv = repo_root / ".venv"
    local_bin = venv_bin_dir(local_venv)
    candidate = local_bin / "openstack"
    if candidate.exists():
        new_env = dict(env)
        new_env["PATH"] = str(local_bin) + os.pathsep + env.get("PATH", "")
        return new_env, str(candidate)

    # Try existing user venv (OSSC path)
    for user_venv in user_venv_paths():
        bin_dir = venv_bin_dir(user_venv)
        openstack_path = bin_dir / "openstack"
        if openstack_path.exists():
            new_env = dict(env)
            new_env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
            return new_env, str(openstack_path)

    # Create and install into the primary venv (first path)
    primary_venv = user_venv_paths()[0]
    bin_dir = venv_bin_dir(primary_venv)
    openstack_path = bin_dir / "openstack"
    if not openstack_path.exists():
        if not (primary_venv / ("pyvenv.cfg")).exists():
            subprocess.check_call([os.sys.executable, "-m", "venv", str(primary_venv)])
        py = str(bin_dir / "python")
        try:
            subprocess.check_call([py, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"]) 
            req = repo_root / "requirements.txt"
            if req.exists():
                subprocess.check_call([py, "-m", "pip", "install", "-r", str(req)])
            else:
                subprocess.check_call([py, "-m", "pip", "install", "python-openstackclient>=6"])
        except subprocess.CalledProcessError:
            pass

    if openstack_path.exists():
        new_env = dict(env)
        new_env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
        return new_env, str(openstack_path)

    exe = shutil.which("openstack", path=env.get("PATH")) or shutil.which("openstack")
    return env, exe
