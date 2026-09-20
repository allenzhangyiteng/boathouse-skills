#!/usr/bin/env python3
"""Install the Boat House skill and authenticated MCP adapter for Muse Code.

No credentials are copied and no account is created. Existing settings are
preserved; conflicting entries are refused instead of silently replaced.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/boathouse"


def settings_path():
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "muse/settings.json"


def prepare_settings(path, script):
    data = json.loads(path.read_text()) if path.exists() else {"schema_version": 1}
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Muse settings must be an object with schema_version 1; nothing was changed.")
    if "mcpServers" in data and "mcp_servers" in data:
        raise ValueError("Muse settings contain both MCP key spellings. Resolve that conflict first.")
    field = "mcp_servers" if "mcp_servers" in data else "mcpServers"
    servers = data.setdefault(field, {})
    if not isinstance(servers, dict):
        raise ValueError("The existing Muse MCP configuration is invalid; nothing was changed.")
    # command/args/framing survive Muse 1.3.0's settings rewrites. Transport is inferred.
    entry = {"command": sys.executable, "args": [str(script)], "framing": "line_delimited_json"}
    env = {}
    for name in ("BH_CONFIG", "XDG_CONFIG_HOME"):
        if os.environ.get(name):
            env[name] = os.environ[name]
    if env:
        entry["env"] = env
    old = servers.get("boathouse")
    if old is not None and old != entry:
        raise ValueError("Muse already has a different boathouse MCP entry. Review it before replacing it; nothing was changed.")
    servers["boathouse"] = entry
    return data


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, indent=2) + "\n"
    if path.exists() and path.read_text() == raw:
        return
    if path.exists():
        fd, backup = tempfile.mkstemp(prefix="settings.boathouse-backup-", suffix=".json", dir=path.parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(path.read_bytes())
    fd, temp = tempfile.mkstemp(prefix=".boathouse-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(raw)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def install(muse):
    path = settings_path()
    target = path.parent / "skills/boathouse"
    script = target / "scripts/mcp_bridge.py"
    data = prepare_settings(path, script)  # validate before any install or mutation
    if target.exists():
        expected = {p.relative_to(SKILL): p.read_bytes() for p in SKILL.rglob("*")
                    if p.is_file() and "__pycache__" not in p.parts}
        if any(not (target / p).is_file() or (target / p).read_bytes() != content for p, content in expected.items()):
            raise ValueError("A different Boat House skill is already installed in Muse. Review/update that skill first; nothing was changed.")
    else:
        result = subprocess.run([muse, "skills", "install", str(SKILL), "--scope", "user", "--json"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode:
            raise ValueError("Muse could not install the Boat House skill. Run muse skills validate on the package for diagnostics.")
    if not script.is_file():
        raise ValueError("Muse did not create the expected skill directory; settings were not changed.")
    atomic_write(path, data)
    print("Boat House installed for Muse Code. Start a new Muse process to load the tools.")
    print("If not already connected, use Copy connection at https://boathousecloud.com/account.")
    print("Ask Muse: Check my Boat House connection, then help me put this app online.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--muse", default=shutil.which("muse"), help="Muse executable, when it is not on PATH")
    args = parser.parse_args()
    if not args.muse:
        parser.error("Install Muse Code from https://dev.meta.ai/products/muse-code first, or pass --muse.")
    try:
        install(args.muse)
    except (OSError, ValueError) as exc:
        # Configuration errors never dump file contents, which can contain other servers' secrets.
        print("Boat House: " + (str(exc) if isinstance(exc, ValueError) and not isinstance(exc, json.JSONDecodeError)
                                 else "Could not read or update Muse configuration; check file permissions and JSON syntax."), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
