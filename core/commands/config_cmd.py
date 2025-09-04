from pathlib import Path
from getpass import getpass
from core.rc import parse_rc_file, build_rc_path
from core.config import load_profiles_config, ensure_profiles_structure, save_profiles_config, config_path


def add_subparser(subparsers):
    cfg_parser = subparsers.add_parser("config", help="Manage stored configurations")
    cfg_sp = cfg_parser.add_subparsers(dest="cfg_cmd", required=True)

    cfg_import = cfg_sp.add_parser("import-rc", help="Import RC file(s) into user config")
    cfg_import.add_argument("--profile", required=True)
    cfg_import.add_argument("--catalog", help="Catalog name for single-file import")
    cfg_import.add_argument("--rc-file", help="Path to RC file; defaults to <profile>/rc-<catalog>.sh (single)")
    cfg_import.add_argument("--rc-dir", help="Directory with rc-*.sh files for batch import")

    cfg_list = cfg_sp.add_parser("list", help="List configured profiles/catalogs")

    cfg_setcred = cfg_sp.add_parser("set-cred", help="Set password for a profile (username comes from RC)")
    cfg_setcred.add_argument("--profile", required=True)
    cfg_setcred.add_argument("--password", help="Password value; if omitted, will prompt")
    return cfg_parser


def handle(args, repo_root: Path):
    profiles, cfg_path, _ = load_profiles_config(repo_root)
    profiles = ensure_profiles_structure(profiles)
    if args.cfg_cmd == "import-rc":
        # Batch mode
        if args.rc_dir:
            from pathlib import Path
            import re

            dir_path = Path(args.rc_dir)
            if not dir_path.is_dir():
                print(f"Not a directory: {dir_path}")
                return 2
            pattern = re.compile(r"^rc[-_](.+)\.sh$", re.IGNORECASE)
            imported = 0
            skipped = 0
            errors = 0
            for p in sorted(dir_path.iterdir()):
                if not p.is_file() or not p.name.lower().endswith('.sh'):
                    continue
                m = pattern.match(p.name)
                catalog = None
                if m:
                    catalog = m.group(1)
                try:
                    env_map = parse_rc_file(p)
                except Exception as e:
                    print(f"[skip] {p.name}: parse error: {e}")
                    errors += 1
                    continue
                if not catalog:
                    catalog = env_map.get("OS_PROJECT_ID")
                if not catalog:
                    print(f"[skip] {p.name}: cannot determine catalog name (no rc-* match and no OS_PROJECT_ID)")
                    skipped += 1
                    continue
                profiles.setdefault("profiles", {}).setdefault(args.profile, {}).setdefault("catalogs", {})[catalog] = {
                    k: v for k, v in env_map.items() if k.startswith("OS_")
                }
                print(f"Imported {p} -> profile '{args.profile}', catalog '{catalog}'")
                imported += 1
            save_profiles_config(config_path(), profiles)
            print(f"Batch import summary: imported={imported}, skipped={skipped}, errors={errors}")
            return 0

        # Single file mode
        if not args.catalog:
            print("--catalog is required for single-file import (use --rc-dir for batch mode)")
            return 2
        rc_path = build_rc_path(repo_root, args.profile, args.catalog, args.rc_file)
        env_map = parse_rc_file(rc_path)
        profiles.setdefault("profiles", {}).setdefault(args.profile, {}).setdefault("catalogs", {})[args.catalog] = {
            k: v for k, v in env_map.items() if k.startswith("OS_")
        }
        save_profiles_config(config_path(), profiles)
        print(f"Imported {rc_path} into profile '{args.profile}', catalog '{args.catalog}'.")
        return 0
    if args.cfg_cmd == "list":
        profs = profiles.get("profiles", {})
        if not profs:
            print("No profiles configured.")
            return 0
        for pname, pdata in profs.items():
            cats = sorted((pdata or {}).get("catalogs", {}).keys())
            cats_str = ", ".join(cats) if cats else "(no catalogs)"
            print(f"{pname}: {cats_str}")
        return 0
    if args.cfg_cmd == "set-cred":
        pw = args.password
        if not pw:
            pw = getpass("OS_PASSWORD (input hidden): ")
            if not pw:
                print("No password provided; nothing changed.")
                return 2
        profiles.setdefault("profiles", {}).setdefault(args.profile, {})["password"] = pw
        save_profiles_config(config_path(), profiles)
        print(f"Updated password for profile '{args.profile}'.")
        return 0
    return 0
