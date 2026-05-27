#!/usr/bin/env python3
"""Setup helper for adgine-geo-skills.

Two ways to run:

  Non-interactive (for AI agents / scripts):
      python3 setup.py <GEO_API_KEY>
      python3 setup.py --key <GEO_API_KEY>

  Interactive wizard (for humans):
      python3 setup.py

Behavior:
  - Locates the skills repo root via this file's own absolute path,
    so it works regardless of the caller's current working directory.
  - Writes GEO_API_KEY to <repo_root>/.env (creating it from
    .env.example if needed). Preserves other lines in .env.
  - Verifies the key by calling /api/projects?limit=1 with Bearer auth.
    Exit code 0 on success, non-zero on failure.
  - Never writes to ~/.zshrc, ~/.bashrc, ~/.hermes/, or any other
    location. The .env file is gitignored — the key stays local.
"""
import os
import sys
import shutil
import argparse

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(REPO_ROOT, ".env")
ENV_EXAMPLE_PATH = os.path.join(REPO_ROOT, ".env.example")
PLACEHOLDER_VALUES = {"", "geo_sk_live_YOUR_KEY_HERE", "geo_sk...HERE"}


def read_env_key():
    """Return the current GEO_API_KEY from .env, or None if unset/placeholder."""
    if not os.path.isfile(ENV_PATH):
        return None
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith("GEO_API_KEY="):
                val = line.split("=", 1)[1].strip()
                return val if val not in PLACEHOLDER_VALUES else None
    return None


def write_env_key(key):
    """Write or update GEO_API_KEY in <repo_root>/.env, preserving other lines."""
    if not os.path.isfile(ENV_PATH):
        if os.path.isfile(ENV_EXAMPLE_PATH):
            shutil.copy(ENV_EXAMPLE_PATH, ENV_PATH)
        else:
            with open(ENV_PATH, "w") as f:
                f.write("# GEO Skills — Environment Variables\n")

    with open(ENV_PATH) as f:
        lines = f.readlines()

    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("GEO_API_KEY="):
            new_lines.append(f"GEO_API_KEY={key}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f"GEO_API_KEY={key}\n")

    with open(ENV_PATH, "w") as f:
        f.writelines(new_lines)


def verify_key(key):
    """Quick auth check. Returns (ok: bool, message: str).

    ok=True means the key is accepted (HTTP 200) OR the platform was
    unreachable (we don't want to block setup on transient network issues).
    ok=False means we got a definitive 401 Unauthorized.
    """
    import urllib.request as req
    import urllib.error as uerr

    base = os.environ.get("GEO_API_BASE_URL", "https://platform.adgine.ai").rstrip("/")
    url = f"{base}/api/projects?limit=1"
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "User-Agent": "geo-skills-setup/1.0",
    }
    request = req.Request(url, headers=headers, method="GET")
    try:
        with req.urlopen(request, timeout=10) as resp:
            return (resp.status == 200, f"HTTP {resp.status}")
    except uerr.HTTPError as e:
        if e.code == 401:
            return (False, "401 Unauthorized — key is invalid")
        # Other errors (403, 5xx) don't necessarily mean the key is wrong.
        return (True, f"HTTP {e.code} (non-auth error, treating as ok)")
    except Exception as e:
        return (True, f"network error: {e} (skipped verification)")


def print_next_steps():
    print("  Next steps:")
    print("  1. List your projects:")
    print("       python3 adgine-geo-projects/scripts/list_projects.py")
    print("  2. Ask your agent, for example:")
    print('       "What\'s my AI visibility score this week?"')
    print()


def run_noninteractive(key):
    """Install the key without prompting. Used by AI agents."""
    if not key or key in PLACEHOLDER_VALUES:
        print("ERROR: empty or placeholder key.", file=sys.stderr)
        sys.exit(2)

    if not key.startswith("geo_sk_"):
        print(
            f"WARNING: key does not start with 'geo_sk_' (got: {key[:8]}...). "
            "Continuing anyway.",
            file=sys.stderr,
        )

    ok, detail = verify_key(key)
    if not ok:
        print(f"ERROR: key verification failed — {detail}", file=sys.stderr)
        print("  Check the key at: https://platform.adgine.ai", file=sys.stderr)
        sys.exit(1)

    write_env_key(key)
    print(f"OK: GEO_API_KEY written to {ENV_PATH}")
    print(f"    verification: {detail}")
    sys.exit(0)


def run_interactive():
    """Wizard for human users."""
    print()
    print("=" * 52)
    print("  adgine-geo-skills — Setup Wizard")
    print("=" * 52)
    print()

    existing_key = read_env_key()

    if existing_key:
        print(f"  GEO_API_KEY already set in {ENV_PATH}")
        print()
        answer = input("  Re-enter / update it? [y/N] ").strip().lower()
        if answer != "y":
            print()
            print("  No changes made. You're ready to go!")
            print()
            print_next_steps()
            return

    print("  Get your API key at: https://platform.adgine.ai")
    print()
    key = input("  Paste your GEO_API_KEY: ").strip()

    if not key or key in PLACEHOLDER_VALUES:
        print()
        print("  No key entered. Run setup.py again when you have your key.")
        sys.exit(1)

    print()
    print("  Verifying key...", end="", flush=True)
    ok, detail = verify_key(key)
    if ok:
        print(f" OK ({detail})")
    else:
        print(f" FAILED ({detail})")
        print()
        print("  Double-check at: https://platform.adgine.ai")
        sys.exit(1)

    write_env_key(key)
    print()
    print(f"  Key saved to: {ENV_PATH}")
    print("  (This file is gitignored — your key stays local and private.)")
    print()
    print_next_steps()


def main():
    parser = argparse.ArgumentParser(
        description="Configure GEO_API_KEY for adgine-geo-skills.",
        add_help=True,
    )
    parser.add_argument(
        "key",
        nargs="?",
        help="GEO_API_KEY to install. Omit for interactive mode.",
    )
    parser.add_argument(
        "--key",
        dest="key_flag",
        help="GEO_API_KEY (alternative to positional argument).",
    )
    args = parser.parse_args()

    key = args.key_flag or args.key
    if key:
        run_noninteractive(key)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
