import argparse
import os
import shlex
import subprocess
import sys
from getpass import getpass
from pathlib import Path

from core.config import (
    load_profiles_config,
    ensure_profiles_structure,
    get_catalog_env,
    resolve_password,
    resolve_username,
    save_profiles_config,
    config_path,
)
from core.env import ensure_openstack_available
from core.rc import parse_rc_file, build_rc_path
from core.commands import config_cmd, report_cmd


KNOWN_OPTS_WITH_VALUE = {
    "--profile",
    "--catalog",
    "--rc-file",
    "--username",
    "--password",
}
KNOWN_FLAGS = {"--dry-run"}


def _first_positional(argv):
    it = iter(enumerate(argv))
    for i, tok in it:
        if tok == "--":
            # Everything after is positional; next token is first positional if exists
            return argv[i + 1] if i + 1 < len(argv) else None
        if tok.startswith("--"):
            if tok in KNOWN_FLAGS:
                continue
            if tok in KNOWN_OPTS_WITH_VALUE:
                # Skip its value if present
                j = i + 1
                if j < len(argv) and not argv[j].startswith("-"):
                    next(it, None)
                continue
            # Unknown option, treat next token normally
            continue
        if tok.startswith("-") and len(tok) > 1:
            # Short flags not used; ignore
            continue
        # Found first positional
        return tok
    return None


def build_parser():
    parser = argparse.ArgumentParser(
        prog="ossc",
        description=(
            "OpenStack CLI wrapper: applies RC/config env and forwards commands."
        ),
        add_help=True,
    )
    subparsers = parser.add_subparsers(dest="subcmd")

    # Subcommands
    config_cmd.add_subparser(subparsers)
    report_cmd.add_subparser(subparsers)

    # Default run-mode args
    parser.add_argument("--profile", required=False, help="Profile name (e.g. dev, prod)")
    parser.add_argument("--catalog", required=False, help="Catalog name (e.g. app, infra)")
    parser.add_argument("--rc-file", help="Override RC file path")
    parser.add_argument("--username", help="Override OS_USERNAME")
    parser.add_argument("--password", help="Override OS_PASSWORD")
    parser.add_argument("--dry-run", action="store_true", help="Print env and command without executing")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to pass to openstack")
    return parser


def build_default_parser():
    parser = argparse.ArgumentParser(
        prog="ossc",
        description=(
            "OpenStack CLI wrapper: applies RC/config env and forwards commands."
        ),
        add_help=True,
    )
    parser.add_argument("--profile", required=False, help="Profile name (e.g. dev, prod)")
    parser.add_argument("--catalog", required=False, help="Catalog name (e.g. app, infra)")
    parser.add_argument("--rc-file", help="Override RC file path")
    parser.add_argument("--username", help="Override OS_USERNAME")
    parser.add_argument("--password", help="Override OS_PASSWORD")
    parser.add_argument("--dry-run", action="store_true", help="Print env and command without executing")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to pass to openstack")
    return parser


def handle_default(args, repo_root: Path):
    if not args.profile or not args.catalog:
        raise SystemExit("--profile and --catalog are required unless using 'config' or 'report'")

    profiles, cfg_path, _ = load_profiles_config(repo_root)
    profiles = ensure_profiles_structure(profiles)
    cfg_env = get_catalog_env(profiles, args.profile, args.catalog) or {}

    if cfg_env:
        rc_env = cfg_env
        rc_source = Path("[config]")
    else:
        rc_source = build_rc_path(repo_root, args.profile, args.catalog, args.rc_file)
        rc_env = parse_rc_file(rc_source)

    profile_entry = profiles.get("profiles", {}).get(args.profile, {})
    need_username = not resolve_username(args, profile_entry, rc_env)
    need_password = not resolve_password(args, profile_entry)
    if sys.stdin.isatty() and (need_username or need_password):
        print("First-time setup for profile '%s'." % args.profile)
        rc_user = rc_env.get("OS_USERNAME") or profile_entry.get("username")
        if need_username:
            prompt_user = input("OS_USERNAME [%s]: " % (rc_user or "")).strip()
            if prompt_user:
                profile_entry["username"] = prompt_user
            elif rc_user:
                profile_entry["username"] = rc_user
        if need_password:
            pw = getpass("OS_PASSWORD (input hidden): ")
            if pw:
                profile_entry["password"] = pw
        if profile_entry:
            profiles.setdefault("profiles", {}).setdefault(args.profile, {}).update(profile_entry)
            save_profiles_config(config_path(), profiles)

    effective_profile = profiles.get("profiles", {}).get(args.profile, {})
    password = resolve_password(args, effective_profile)
    username = resolve_username(args, effective_profile, rc_env)

    env = os.environ.copy()
    env.update(rc_env)
    if username:
        env["OS_USERNAME"] = username
    if password:
        env["OS_PASSWORD"] = password

    missing = [k for k in ("OS_AUTH_URL", "OS_USERNAME", "OS_PASSWORD") if not env.get(k)]
    if missing:
        print("Missing required variables: %s" % ", ".join(missing), file=sys.stderr)
        return 2

    cmd = ["openstack"]
    if args.command:
        parts = args.command
        if parts and parts[0] == "--":
            parts = parts[1:]
        cmd.extend(parts)

    if args.dry_run:
        safe_env = {k: ("***" if k in ("OS_PASSWORD",) else v) for k, v in env.items() if k.startswith("OS_")}
        print("RC source:", rc_source)
        print("Resolved OS_* env:")
        for k in sorted(safe_env):
            print("  %s=%s" % (k, safe_env[k]))
        print("Command:", " ".join(shlex.quote(c) for c in cmd))
        return 0

    try:
        env, openstack_exe = ensure_openstack_available(repo_root, env)
    except subprocess.CalledProcessError as e:
        print("Failed to bootstrap virtualenv for openstackclient:", e, file=sys.stderr)
        return 127
    if openstack_exe:
        cmd[0] = openstack_exe
    else:
        print("'openstack' CLI not found and auto-setup failed. See README for manual setup.", file=sys.stderr)
        return 127

    proc = subprocess.run(cmd, env=env)
    return proc.returncode


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    first_pos = _first_positional(argv)
    # Route to subcommands only if the first positional is a known subcommand
    if first_pos in {"config", "report"}:
        parser = build_parser()
        args = parser.parse_args(argv)
    else:
        parser = build_default_parser()
        args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parent.parent

    if getattr(args, "subcmd", None) == "config":
        return config_cmd.handle(args, repo_root)
    if getattr(args, "subcmd", None) == "report":
        return report_cmd.handle(args, repo_root)
    return handle_default(args, repo_root)
