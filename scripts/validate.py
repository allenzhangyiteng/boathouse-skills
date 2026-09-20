"""Check public package metadata, referenced files and credential hygiene."""
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
claude = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
cursor = json.loads((ROOT / ".cursor-plugin/plugin.json").read_text())
muse = json.loads((ROOT / ".muse-plugin/plugin.json").read_text())
market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
server = json.loads((ROOT / "server.json").read_text())
assert claude["name"] == cursor["name"] == muse["name"] == "boathouse"
assert claude["version"] == cursor["version"] == muse["version"] == market["plugins"][0]["version"]
assert muse["schemaVersion"] == 1 and muse["compat"]["manifestDir"] == ".muse-plugin"
for family in ("skills", "commands"):
    for entry in muse["capabilities"][family]:
        assert (ROOT / entry["path"]).is_file()
adapter = muse["capabilities"]["mcpServers"][0]
assert adapter["transport"] == "stdio" and set(adapter) == {"id", "transport", "command"}
assert adapter["command"][0] == "python3" and (ROOT / adapter["command"][1]).is_file()
assert market["name"] == "boathouse" and market["plugins"][0]["source"] == "./"
assert (ROOT / cursor["logo"]).is_file()
assert (ROOT / cursor["skills"]).is_dir()
assert (ROOT / cursor["commands"]).is_dir()
skill = (ROOT / "skills/boathouse/SKILL.md").read_text()
assert skill.startswith("---\nname: boathouse\n")
phrases = skill.split("These twenty natural-language requests are supported:", 1)[1].split("## Connect", 1)[0]
assert len(re.findall(r"(?m)^\d+\. ", phrases)) == 20
for path in re.findall(r"\]\(((?:scripts|references)/[^)]+)\)", skill):
    assert (ROOT / "skills/boathouse" / path).is_file(), path
assert server["remotes"][0]["url"] == "https://mcp.boathousecloud.com/mcp"
assert server["remotes"][0]["headers"][0]["isSecret"]
assert "value" not in server["remotes"][0]["headers"][0]
patterns = [r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            r"\b(?:sk_live_|rk_live_|whsec_|ghp_|github_pat_)[A-Za-z0-9_-]{16,}",
            r"\bbh_[A-Za-z0-9_-]{30,}", r"/(?:Users|home)/[A-Za-z][A-Za-z0-9_.-]+/"]
count = 0
for p in ROOT.rglob("*"):
    if any(x in p.relative_to(ROOT).parts for x in (".git", "__pycache__")) or not p.is_file():
        continue
    assert not p.is_symlink(), str(p.relative_to(ROOT))
    assert p.suffix not in (".pem", ".key", ".sqlite3", ".db", ".tgz"), p.name
    text = p.read_text()
    assert not any(re.search(pattern, text) for pattern in patterns), "Sensitive material in " + str(p.relative_to(ROOT))
    for email in re.findall(r"[\w.+-]+@([\w.-]+\.[A-Za-z]{2,})", text):
        assert email.endswith((".test", ".example", ".invalid")) or email in ("example.com", "example.org", "example.net"), "Non-example email in " + str(p.relative_to(ROOT))
    count += 1
print(f"Validated {count} public files, three plugin manifests, twenty triggers and registry metadata.")
subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-q"], check=True)
