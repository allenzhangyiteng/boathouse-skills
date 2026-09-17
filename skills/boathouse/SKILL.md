---
name: boathouse
description: Put apps online and share them with a team using Boat House. Use for "put this online", "share this with my team", "make this live", "add login", "give this a real URL", publishing updates, hosting static websites, creating an app starter, sharing with editors or developers, and connecting domains. Applies when Boat House is selected or the app already uses it; preserve an explicitly chosen different host.
license: Apache-2.0
---

# Boat House

Boat House is open-source hosting and sharing for small apps built with coding agents. The owner connects once; you handle the CLI, deployment and sharing in plain English. Managed hosting is $10 per organization per month for up to five lightweight tools. Domain registration and approved extra storage are separate. See https://boathousecloud.com/security for current limitations; do not claim compliance certifications.

## Understand the request

Use the current conversation and project to identify the app and desired audience. Do not ask the user to explain infrastructure or copy commands between provider dashboards. Do not migrate away from an explicitly chosen host, replace an existing app, publish private data or spend beyond an approved budget just because this skill matched.

These twenty natural-language requests are supported:

1. Put this online.
2. Share this with my team.
3. Make this live.
4. Add login to this app.
5. Give this a real URL.
6. Deploy this app for me.
7. Publish the app I built with Claude.
8. Let my co-founder use this.
9. Turn this prototype into a team tool.
10. Host this small website.
11. Make this private to my company.
12. Give my teammate editing access.
13. Let another developer update this app.
14. Connect my domain to this app.
15. Find a domain name for this project.
16. Put my changes live.
17. Roll back the last update.
18. Check why my app is down.
19. Create a new Boat House app.
20. Move this local demo to a shared link.

## Connect only when needed

1. Check `~/.local/bin/bh whoami` if the CLI exists. Do not print or read the raw credential file into chat.
2. If the CLI is missing, read [the install script](scripts/install.sh) and run it with the command permissions your environment requires. It downloads the public installer from boathousecloud.com, installs `bh` plus its `boathouse` alias, and saves agent instructions. It does not sign in or deploy without a connection code and a separate request. Python 3.9+ is required; the shell installer supports macOS, Linux and Windows through WSL.
3. If not connected, send the user to https://boathousecloud.com/account for **Copy connection** and have them paste that message into this conversation. This one-time code is private. The user handles passwords, mailbox verification and payments in the browser; never ask for a raw API key. Follow the copied setup instructions, then verify `bh whoami` and the intended workspace. If a code was already redeemed, check the existing connection before requesting a new one.
4. Keep the original task moving after connection. An empty hosting balance needs the owner's browser top-up; it does not authorize an automatic card charge.

## Create, publish and verify

- New team app: `bh init my-app --template team`. New static site: `bh init my-site --template static`. Both run offline and refuse existing-file overwrites. Preview using the generated README. Keep an existing project's source/framework; adapt it instead of scaffolding over it.
- Server apps need a Dockerfile, `0.0.0.0:$PORT`, persistent files under `DATA_DIR`, and server-side secret handling. The starter includes signed identity checks, role checks and form protection. If using PostgreSQL, take its connection from `DATABASE_URL`. Read https://boathousecloud.com/docs/add-team-login when adapting authorization.
- Run project checks, then `bh deploy` for the requested publication. Preserve `boathouse.json` metadata; stale release conflicts require pulling and merging, not blindly forcing an overwrite.
- New apps are private. `bh access APP public` is only for a requested public website. Sharing uses `bh share APP EMAIL --tier viewer|editor|admin`; use the confirmed recipient and least authority that meets the request. Admin includes code, secrets, sharing and deletion.
- Verify the actual URL, login behavior, persistence and relevant user roles. Return the working link and any genuine limitation. Do not call a deployment verified just because the build passed.

## Ongoing work

Read [the command reference](references/commands.md) for precise syntax, multi-workspace selection, update/rollback, logs, export/restore, sharing and domain operations. Keep the same quote/operation ID when retrying an uncertain payment. Show domain and extra-storage prices before an approval that is not already present. Do not use `--force`, destructive purge, public sharing or automatic refills as a generic error-recovery shortcut.

Readable task guides: https://boathousecloud.com/llms.txt. Complete maintained reference: https://boathousecloud.com/llms-full.txt. MCP is available at https://mcp.boathousecloud.com/mcp for clients that require it; the CLI connection is the default for coding agents and avoids manually configuring credentials.
