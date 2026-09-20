# Boat House for your coding agent

**Put your app online. Share it with your team. Keep the code and data yours.**

An Apache 2.0 skill and connector for [Boat House](https://boathousecloud.com). Use Claude Code, Cursor, Codex, Windsurf or Muse Code to publish a small app with team login, persistent data and a stable HTTPS link. Viewers and editors use the app in a browser; trusted developers can update it from their own agent.

## Install the skill

```sh
npx skills add allenzhangyiteng/boathouse-skills
```

Select your agent, or install into Cursor, Codex and Windsurf together:

```sh
npx skills add allenzhangyiteng/boathouse-skills --skill boathouse --agent cursor codex windsurf --yes
```

Add `--global` to make the skill available across projects. The current skills installer requires Node.js 22.20+; the Boat House CLI requires Python 3.9+. The skill installs the CLI on first use after checking for an existing installation. No deployment or payment happens on installation.

## Claude Code plugin

Inside Claude Code, register the marketplace once, then install:

```text
/plugin marketplace add allenzhangyiteng/boathouse-skills
/plugin install boathouse@boathouse
```

Then use `/boathouse:setup` or say **“Put this app online with Boat House.”** This is our own marketplace; do not interpret it as an official-directory approval. The plugin has no startup hooks and contains no credentials.

## Meta Muse / Muse Code

For the current Muse Code release, install the skill and authenticated MCP connector together:

```sh
git clone https://github.com/allenzhangyiteng/boathouse-skills.git
python3 boathouse-skills/scripts/install_muse.py
```

Start a new Muse session, connect Boat House once, then ask **“Put this app online for my team.”** The connector reuses the private connection created by `bh`; no extra API-key copying is needed. It preserves existing Muse settings and keeps its approval controls enabled.

A native Muse plugin manifest is also included for plugin-enabled builds. The public Muse Code 1.3.0-R3401.1 build tested on September 20, 2026 did not enable plugins, so use the MCP installer above. [Full Muse guide, requirements and web/mobile limitations](skills/boathouse/references/muse.md).

## Connect once

Sign up at [Boat House](https://boathousecloud.com/signup), confirm your email, then paste **Copy connection** from your account into the agent conversation containing your app. The agent installs the CLI, redeems the one-time code and checks the selected organization. You handle passwords and payments in your browser.

After that, ask things like “share this with my team”, “make this live”, “add login”, “give this a real URL” or “put my changes live”. The skill includes twenty request examples and preserves your choices about access and spending.

## Start an app locally

For a CLI-only install on macOS/Linux/WSL:

```sh
curl -fsSL https://boathousecloud.com/install.sh -o /tmp/boathouse-install.sh
sh /tmp/boathouse-install.sh
~/.local/bin/boathouse init my-app --template team
cd my-app
python3 app.py --local
```

Open http://127.0.0.1:8080. Use `--template static` for a website. Local creation and preview do not need a Boat House account. The alias is installed only when its filename is available; `~/.local/bin/bh` always works after successful installation.

## What it can do

- Publish a Docker app or static website, with version history and rollback.
- Share Viewer, Editor or Admin access by email; Admin controls code and secrets too.
- Use persistent files or the included PostgreSQL database.
- Connect a domain, or show a quote before an authorized purchase.
- Read logs, export source/data and restore backups.

Managed hosting costs **$10 per organization per month for up to five lightweight tools**, from prepaid credit. Domain purchases and approved extra storage are separate. Self-hosting the [core](https://github.com/allenzhangyiteng/boathouse-cloud) has no software license fee; infrastructure costs remain.

## Documentation and security

[Question-based guides](https://boathousecloud.com/docs) · [llms.txt](https://boathousecloud.com/llms.txt) · [Complete agent docs](https://boathousecloud.com/llms-full.txt) · [Security model](https://boathousecloud.com/security)

Installing a skill does not grant blanket permission to publish, spend or share. Keep one-time connection codes and account keys private. Use ordinary low-sensitivity workloads within the current security scope; no SOC 2, ISO 27001 or HIPAA assurance is claimed. An app must enforce its own data permissions.

Advanced MCP clients can connect to `https://mcp.boathousecloud.com/mcp` using the account's advanced connection settings. `server.json` describes the remote endpoint for registry publication. Registry listing and vendor-directory review are separate from installing this repository.

## Package layout

`skills/boathouse` is the portable skill and includes the standard-library MCP adapter. `.claude-plugin` contains the Claude plugin and marketplace manifests; `.cursor-plugin` contains Cursor metadata; `.muse-plugin` contains the native Muse preview manifest. `scripts/install_muse.py` installs the supported Muse Code skill/MCP configuration. No private account state or production credentials are included.
