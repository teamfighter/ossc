import os
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

from core.config import load_profiles_config, ensure_profiles_structure, get_catalog_env, resolve_password, resolve_username
from core.env import ensure_openstack_available


def add_subparser(subparsers):
    rpt = subparsers.add_parser("report", help="Generate summary reports per profile/catalog")
    rpt.add_argument("--out", default="out/reports", help="Output directory for reports")
    rpt.add_argument("-f", "--format", choices=["csv", "json", "table", "value", "yaml"], default="table", help="the output format, defaults to table")
    return rpt


def handle(args, repo_root: Path):
    profiles, cfg_path, _ = load_profiles_config(repo_root)
    profiles = ensure_profiles_structure(profiles)
    prof_map = profiles.get("profiles", {})
    if not prof_map:
        print("No profiles configured. Import RCs first via 'ossc config import-rc'.")
        return 2

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    # Determine scope based on optional filters
    filter_profile = getattr(args, "profile", None)
    filter_catalog = getattr(args, "catalog", None)

    # Build a list of (profile, catalog, rc_env) to process
    tasks = []
    if filter_profile and filter_catalog:
        pdata = prof_map.get(filter_profile)
        if not pdata:
            print(f"Profile not found: {filter_profile}")
            return 2
        rc_env = (pdata.get("catalogs", {}) or {}).get(filter_catalog)
        if not rc_env:
            print(f"Catalog not found in profile '{filter_profile}': {filter_catalog}")
            return 2
        tasks.append((filter_profile, filter_catalog, rc_env, pdata))
    elif filter_profile and not filter_catalog:
        pdata = prof_map.get(filter_profile)
        if not pdata:
            print(f"Profile not found: {filter_profile}")
            return 2
        catalogs = (pdata or {}).get("catalogs", {})
        if not catalogs:
            print(f"No catalogs configured for profile '{filter_profile}'.")
            return 2
        for catalog, rc_env in catalogs.items():
            tasks.append((filter_profile, catalog, rc_env, pdata))
    elif not filter_profile and filter_catalog:
        # Process this catalog across all profiles that have it
        found = False
        for prof, pdata in prof_map.items():
            rc_env = (pdata.get("catalogs", {}) or {}).get(filter_catalog)
            if rc_env:
                tasks.append((prof, filter_catalog, rc_env, pdata))
                found = True
        if not found:
            print(f"Catalog not found in any profile: {filter_catalog}")
            return 2
    else:
        # No filters provided: process all profiles/catalogs
        for prof, pdata in prof_map.items():
            catalogs = (pdata or {}).get("catalogs", {})
            if not catalogs:
                continue
            for catalog, rc_env in catalogs.items():
                tasks.append((prof, catalog, rc_env, pdata))

    exit_code = 0
    for prof, catalog, rc_env, pdata in tasks:
            # Build env
            env = os.environ.copy()
            env.update(rc_env)
            username = resolve_username(args, pdata, rc_env)
            password = resolve_password(args, pdata)
            if username:
                env["OS_USERNAME"] = username
            if password:
                env["OS_PASSWORD"] = password

            missing = [k for k in ("OS_AUTH_URL", "OS_USERNAME", "OS_PASSWORD") if not env.get(k)]
            report_dir = out_root / prof / catalog
            report_dir.mkdir(parents=True, exist_ok=True)
            report_file = report_dir / "report.txt"

            if missing:
                report_file.write_text(
                    f"[{datetime.utcnow().isoformat()}Z] Missing variables: {', '.join(missing)}\n",
                    encoding="utf-8",
                )
                exit_code = exit_code or 2
                continue

            # Ensure openstack
            try:
                env, openstack_exe = ensure_openstack_available(repo_root, env)
            except subprocess.CalledProcessError as e:
                report_file.write_text(f"Bootstrap failed: {e}\n", encoding="utf-8")
                exit_code = exit_code or 127
                continue
            if not openstack_exe:
                report_file.write_text("OpenStack CLI not found.\n", encoding="utf-8")
                exit_code = exit_code or 127
                continue

            cmd = [openstack_exe, "server", "list", "-f", args.format]
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
            header = (
                f"# Report: server list\n# Profile: {prof}\n# Catalog: {catalog}\n# Format: {args.format}\n"
                f"# Time: {datetime.utcnow().isoformat()}Z\n# Command: {' '.join(shlex.quote(c) for c in cmd)}\n\n"
            )
            content = header + (proc.stdout or "")
            if proc.returncode != 0:
                content += f"\n[exit={proc.returncode}] stderr:\n{proc.stderr or ''}"
            report_file.write_text(content, encoding="utf-8")
            exit_code = exit_code or proc.returncode

    return exit_code
