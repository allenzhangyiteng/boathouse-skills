# Boat House in Meta Muse

Boat House connects Muse to managed app hosting, team login, persistent data,
sharing, updates, logs and domains. The adapter uses the existing Boat House
MCP service and permissions. The package is Apache-2.0 licensed. Managed hosting
is paid; installing the connector does not spend money.

## Muse Code: supported installation

Muse Code 1.3.0-R3401.1 supports standalone skills and configured MCP servers.
The publicly downloaded build tested on September 20, 2026 returned
`plugins are not available in this build`. Use this supported path today:

```sh
git clone https://github.com/allenzhangyiteng/boathouse-skills.git
python3 boathouse-skills/scripts/install_muse.py
```

Run these commands through the agent. If the repository already exists, use the
reviewed checkout rather than overwriting it. Python 3.9+ and Muse Code are
required. If Muse is not on PATH, pass `--muse /path/to/muse` to the installer.
Install Muse itself only from https://dev.meta.ai/products/muse-code.

Muse Code also needs its own Meta sign-in and model API access. In the tested
public build, Meta required a payment method before it enabled that access.
This is separate from Boat House hosting credit. The agent should start
`muse login`, open the fresh device-authorization link and verify that the
command finishes with `Model API access verified`. Signing into Meta's website
alone does not complete the local authorization. If Meta rejects access for
missing billing, finish Meta billing first, then start a fresh login; reusing
an expired device code will not work. Never ask for a password or payment-card
details in chat.

The installer adds the skill using Muse's own skill installer and adds a
`boathouse` stdio MCP entry to the user's Muse settings. It preserves other
settings and servers, makes a private backup before changing existing settings,
and refuses conflicting Boat House entries. It does not disable approvals or
the sandbox. Repeating an unchanged install is safe. Start a new Muse process
after installing. `/mcp` shows whether the tools connected.

Connect once using **Copy connection** at https://boathousecloud.com/account.
The agent follows the copied instructions to redeem the one-time code. The
user handles sign-in and payments in the browser. The adapter reads the same
private config as `bh`, on each call; no token is written into the plugin or
Muse settings. Then ask: **Check my Boat House connection and put this app
online for my team.**

## Plugin-enabled Muse Code builds

The repository also includes a native `.muse-plugin/plugin.json`. In a build
that supports plugins:

```sh
muse plugins validate ./boathouse-skills
muse plugins install ./boathouse-skills
muse plugins inspect boathouse
```

Review and approve the `cloud` MCP capability using Muse's approval UI or the
syntax shown by `muse plugins approve --help`, then start a new Muse process.
`/boathouse:setup` guides connection. This is a preview-format package, not a
claim of Meta marketplace approval. Use either this path or the standalone
MCP installer to avoid duplicate tool entries.

Muse's plugin HTTP entries cannot carry authentication headers. Our plugin
instead starts the included Python stdio adapter; the adapter reads the local
Boat House connection and attaches authentication only to the fixed official
HTTPS endpoint. It does not follow redirects, guess between multiple accounts,
or automatically retry a failed change or purchase.

## Muse personal agent on web/mobile

Muse Code installation commands are not a web/mobile connector catalog entry.
For Muse's custom-integration workflow, give Muse this instruction:

> Read https://github.com/allenzhangyiteng/boathouse-skills and its Muse connection
> guide. Connect Boat House to help me publish and share small apps. Use the
> Boat House CLI in your Linux environment and the one-time Copy connection
> message from my Boat House account. Verify my organization before making
> changes. Do not ask for a raw API key. Ask before purchases or sharing with
> new people, and keep my app private unless I request public access.

The CLI and adapter can run in a Python-capable Linux environment. This path
has not been verified inside a signed-in Muse personal-agent session. Do not
claim a native Muse web/mobile connector or directory listing until that
separate integration is actually accepted and tested.

## Connection details and troubleshooting

- Managed remote endpoint: `https://mcp.boathousecloud.com/mcp` (Streamable HTTP).
- Local adapter: `skills/boathouse/scripts/mcp_bridge.py` (newline JSON stdio).
- Credentials: `BH_CONFIG`, otherwise XDG `boathouse/config.json`, then the
  `~/.boathouse/config.json` fallback used by `bh`. `BH_API`/`BH_KEY` can be supplied
  securely by a host that supports environment configuration. Never embed keys
  in a public repository, command argument, prompt, or URL.
- Muse clears most child environment variables. The standalone installer
  explicitly forwards `BH_CONFIG`/`XDG_CONFIG_HOME` paths when needed; it does not
  copy key values. Plugin users with nonstandard config locations should use
  the standalone installer instead.
- No connection: follow Copy connection. Expired or revoked key: reconnect.
- Multiple accounts: select one connection deliberately; ambiguous matches fail.
- Multiple organizations: call `whoami`, then supply `workspace` explicitly.
- Self-hosted Boat House: use its own remote MCP settings. This adapter refuses
  to send a self-hosted credential to the managed service.
- Timeout during a change: inspect status first. Never blindly repeat a purchase.
- To uninstall the standalone connector, remove only `mcpServers.boathouse`
  (or `mcp_servers.boathouse`) from Muse settings and run
  `muse skills uninstall boathouse`. Your Boat House account and apps remain.

Sources: [Muse MCP configuration](https://meta-models.github.io/muse-code-sdk/next/guides/extend/mcp-servers/),
[plugin manifest](https://meta-models.github.io/muse-code-sdk/next/guides/plugins/reference/manifest/),
[standalone skills](https://meta-models.github.io/muse-code-sdk/next/guides/extend/skills/).
