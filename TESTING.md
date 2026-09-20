# Muse connector verification

Verified September 20, 2026 with the official public Muse Code
`1.3.0-R3401.1` build on macOS.

## Completed

- Fresh standalone skill/MCP installation and repeated installation.
- Muse's own skill validator: valid, common Agent Skills profile.
- Actual Muse runtime discovery of all 41 Boat House MCP tools.
- A signed-in Meta `muse-spark-1.3` model called the live `prices` MCP tool and
  correctly reported the $10 organization plan with five lightweight tools.
  The test exposed only public pricing to Meta; account identity and billing
  were checked locally. Meta account authorization and model API access passed.
- An actual Muse tool invocation reached the live managed MCP service and
  returned the explicitly selected QA organization. This transport test used
  a **local scripted model provider**, not Meta's model; no private account
  data was sent to an external model.
- Live stdio initialize, tool discovery, identity, billing and pricing calls.
- A deployment to an empty, unfunded QA organization was refused with a clear
  payment-required result. No app was created and its balance was unchanged.
- 28 adapter/installer tests: account selection, credential rotation, missing
  and invalid credentials, redaction, redirect rejection, no mutation retries,
  conservative tool annotations, config preservation, backups and repeatability.
- 44 existing core MCP regression tests, covering protocol, permissions,
  deployment inputs, sharing, source, releases, rollback and payment guards.
- Public-package credential scan: no leaks found.

## Not yet verified

- A successful hosted deployment driven by the signed-in Meta model, and
  integration with the separate Muse personal agent on web/mobile.
- A fresh successful hosted deployment through this connector: the available
  QA organization had no prepaid hosting credit. The core deployment regression
  tests do not replace that live check.
- Native plugin installation: the public binary reports `plugins are not
  available in this build`. The native manifest follows Meta's preview
  specification, but the standalone installer is the verified release path.
- Meta marketplace acceptance or listing; neither is implied by this package.

## Run checks

```sh
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
muse skills validate skills/boathouse --json
python3 tests/live_muse_smoke.py --workspace YOUR_QA_WORKSPACE
```

The live smoke test uses the existing private Boat House connection. For a
dedicated empty QA organization with zero balance, add
`--verify-unfunded-deploy` to test the payment guard. It does not top up, change
balances, buy domains, invite people or touch another organization.
