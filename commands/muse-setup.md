---
description: Connect Muse to Boat House and verify the selected organization.
---

Read the Boat House skill included in this plugin. Check the existing connection before asking the user to connect again. If needed, use the skill's CLI installer and the user's one-time **Copy connection** message from https://boathousecloud.com/account. The user handles sign-in, email verification and payments in the browser. Never print the credential file or ask for a raw API key.

The plugin's `cloud` MCP capability is a Python standard-library adapter to https://mcp.boathousecloud.com/mcp. It reads the same local Boat House login as `bh`, on each tool call. It has no startup hooks and does not deploy or spend during setup. Review and approve only this capability using `muse plugins inspect boathouse` and the approval command documented by `muse plugins approve --help`; preserve Muse's approval policy. A new Muse process is required after first approving the MCP capability.

Call the connected Boat House `whoami` tool and confirm the organization before any mutation. In multi-organization accounts, supply `workspace` explicitly on each tool call. If MCP is not active yet, verify with `bh whoami` and explain that a fresh Muse session loads the approved tools. Return to the user's original task after connection. Installation or connection alone does not authorize deployment, invitations, domain purchases or payments.
