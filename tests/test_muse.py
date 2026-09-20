import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge = load("bridge", "skills/boathouse/scripts/mcp_bridge.py")
installer = load("installer", "scripts/install_muse.py")
KEY = "test-credential-not-real"


def call(name="whoami", **args):
    return {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": name, "arguments": args}}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "config.json"
        self.env = patch.dict(os.environ, {"BH_CONFIG": str(self.path)}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def save(self, **changes):
        data = {"logins": [{"api": bridge.API, "key": KEY, "workspace": "*"}], "default": "acme"}
        data.update(changes)
        self.path.write_text(json.dumps(data))

    def transport(self, response=None, error=None):
        opener = Mock()
        if error:
            opener.open.side_effect = error
        else:
            response = response or {"jsonrpc": "2.0", "id": 7, "result": {"content": []}}
            opener.open.return_value.__enter__ = Mock(return_value=io.BytesIO(json.dumps(response).encode()))
            opener.open.return_value.__exit__ = Mock(return_value=False)
        return opener

    def test_missing_connection_never_uses_network(self):
        op = self.transport()
        result = bridge.forward(call(), op)
        self.assertTrue(result["result"]["isError"])
        self.assertIn("Copy connection", str(result))
        op.open.assert_not_called()

    def test_default_workspace_auth_and_origin(self):
        self.save()
        op = self.transport()
        bridge.forward(call(), op)
        request = op.open.call_args.args[0]
        self.assertEqual(request.full_url, bridge.ENDPOINT)
        self.assertEqual(request.get_header("Authorization"), "Bearer " + KEY)
        self.assertEqual(request.get_header("Boathouse-workspace"), "acme")
        self.assertNotIn(KEY, request.data.decode())

    def test_explicit_workspace_overrides_default(self):
        self.save()
        self.assertEqual(bridge.connection(call(workspace="second"))[0]["Boathouse-Workspace"], "second")

    def test_qualified_tool_selects_organization(self):
        self.save()
        self.assertEqual(bridge.connection(call("get_tool", tool="second/app"))[0]["Boathouse-Workspace"], "second")

    def test_conflicting_workspace_fails_before_network(self):
        self.save()
        op = self.transport()
        self.assertTrue(bridge.forward(call(tool="second/app", workspace="acme"), op)["result"]["isError"])
        op.open.assert_not_called()

    def test_workspace_header_injection_rejected(self):
        self.save()
        with self.assertRaises(bridge.ConnectionProblem):
            bridge.connection(call(workspace="acme\r\nAuthorization: injected"))

    def test_config_reloaded_for_each_call(self):
        self.save()
        self.assertEqual(bridge.connection(call())[1], KEY)
        self.save(logins=[{"api": bridge.API, "key": "rotated-test-value", "workspace": "*"}])
        self.assertEqual(bridge.connection(call())[1], "rotated-test-value")

    def test_legacy_single_login(self):
        self.path.write_text(json.dumps({"api": bridge.API, "key": KEY, "workspace": "acme"}))
        self.assertEqual(bridge.connection(call())[0]["Boathouse-Workspace"], "acme")

    def test_exact_workspace_key_beats_account_key(self):
        self.save(logins=[{"api": bridge.API, "key": KEY, "workspace": "*"},
                          {"api": bridge.API, "key": "scoped-test-value", "workspace": "acme"}])
        self.assertEqual(bridge.connection(call())[1], "scoped-test-value")

    def test_ambiguous_accounts_not_guessed(self):
        self.save(logins=[{"api": bridge.API, "key": KEY, "workspace": "*"}] * 2)
        with self.assertRaises(bridge.ConnectionProblem):
            bridge.connection(call())

    def test_wrong_workspace_key_not_used(self):
        self.save(logins=[{"api": bridge.API, "key": KEY, "workspace": "other"}])
        with self.assertRaises(bridge.ConnectionProblem):
            bridge.connection(call())

    def test_self_hosted_key_never_sent_to_managed_host(self):
        self.save(logins=[{"api": "https://api.example.test", "key": KEY, "workspace": "acme"}])
        op = self.transport()
        self.assertTrue(bridge.forward(call(), op)["result"]["isError"])
        op.open.assert_not_called()

    def test_corrupt_config_not_exposed(self):
        self.path.write_text('{"secret": "' + KEY)
        result = bridge.forward(call(), self.transport())
        self.assertNotIn(KEY, str(result))
        self.assertTrue(result["result"]["isError"])

    def test_bad_key_rejected(self):
        self.save(logins=[{"api": bridge.API, "key": "bad\nheader", "workspace": "acme"}])
        with self.assertRaises(bridge.ConnectionProblem):
            bridge.connection(call())

    def test_initialize_without_login_rewrites_instructions(self):
        op = self.transport({"jsonrpc": "2.0", "id": 7, "result": {"instructions": "ask for a key"}})
        result = bridge.forward({"jsonrpc": "2.0", "id": 7, "method": "initialize", "params": {}}, op)
        self.assertIn("Copy connection", result["result"]["instructions"])
        self.assertIsNone(op.open.call_args.args[0].get_header("Authorization"))

    def test_notifications_silent(self):
        op = self.transport()
        self.assertIsNone(bridge.forward({"jsonrpc": "2.0", "method": "notifications/initialized"}, op))
        op.open.assert_not_called()

    def test_readonly_metadata_keeps_mutations_conservative(self):
        op = self.transport({"jsonrpc":"2.0","id":7,"result":{"tools":[
            {"name":"whoami"},{"name":"deploy"},{"name":"domain_buy"},{"name":"capacity"},
            {"name":"domain_renewal_set"},{"name":"future_tool"}]}})
        r = bridge.forward({"jsonrpc":"2.0","id":7,"method":"tools/list"},op)
        tools = r['result']['tools']
        self.assertTrue(tools[0]['annotations']['readOnlyHint'])
        for tool in tools[1:]:
            self.assertFalse(tool['annotations']['readOnlyHint'])
            self.assertTrue(tool['annotations']['destructiveHint'])

    def test_redirects_refused(self):
        with self.assertRaises(bridge.ConnectionProblem):
            bridge.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.test")

    def test_timeout_on_mutation_never_retries(self):
        self.save()
        op = self.transport(error=URLError("sensitive internal error"))
        result = bridge.forward(call("domain_buy", domain="example.test", confirm=True), op)
        self.assertEqual(op.open.call_count, 1)
        self.assertIn("may have completed", str(result))
        self.assertNotIn("sensitive internal", str(result))

    def test_http_errors_never_echo_response_body(self):
        self.save()
        for status in (401, 403, 500):
            op = self.transport(error=HTTPError(bridge.ENDPOINT, status, KEY, {}, io.BytesIO(KEY.encode())))
            result = bridge.forward(call(), op)
            self.assertNotIn(KEY, str(result))
            self.assertTrue(result["result"]["isError"])

    def test_active_credential_redacted_from_upstream_result(self):
        self.save()
        op = self.transport({"jsonrpc": "2.0", "id": 7, "result": {"content": [{"text": KEY}]}})
        self.assertNotIn(KEY, str(bridge.forward(call(), op)))

    def test_request_id_mismatch_rejected(self):
        self.save()
        op = self.transport({"jsonrpc": "2.0", "id": 999, "result": {}})
        self.assertTrue(bridge.forward(call(), op)["result"]["isError"])

    def test_stdio_bad_json_then_missing_login(self):
        result = subprocess.run([sys.executable, str(ROOT / "skills/boathouse/scripts/mcp_bridge.py")],
                                input='not json\n'+json.dumps(call())+'\n', text=True, capture_output=True, timeout=5)
        replies = [json.loads(x) for x in result.stdout.splitlines()]
        self.assertEqual(replies[0]["error"]["code"], -32700)
        self.assertTrue(replies[1]["result"]["isError"])
        self.assertEqual(result.stderr, "")


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "settings.json"
        self.script = Path(self.temp.name) / "mcp_bridge.py"

    def test_preserves_existing_settings_and_servers(self):
        self.path.write_text(json.dumps({"schema_version": 1, "approval_mode": "on-request",
                                        "mcpServers": {"other": {"url": "https://example.test/mcp"}}}))
        data = installer.prepare_settings(self.path, self.script)
        self.assertEqual(data["approval_mode"], "on-request")
        self.assertIn("other", data["mcpServers"])
        self.assertNotIn("BH_KEY", data["mcpServers"]["boathouse"].get("env", {}))

    def test_legacy_root_preserved_without_conflict(self):
        self.path.write_text('{"schema_version": 1, "mcp_servers": {}}')
        data = installer.prepare_settings(self.path, self.script)
        self.assertNotIn("mcpServers", data)
        self.assertIn("boathouse", data["mcp_servers"])

    def test_conflicting_existing_entry_refused(self):
        original = '{"schema_version":1,"mcpServers":{"boathouse":{"url":"https://example.test/mcp"}}}'
        self.path.write_text(original)
        with self.assertRaises(ValueError):
            installer.prepare_settings(self.path, self.script)
        self.assertEqual(self.path.read_text(), original)

    def test_dual_root_refused(self):
        self.path.write_text('{"schema_version":1,"mcpServers":{},"mcp_servers":{}}')
        with self.assertRaises(ValueError):
            installer.prepare_settings(self.path, self.script)

    def test_atomic_update_backup_and_repeated_install(self):
        original = '{"schema_version":1,"other":"keep"}'
        self.path.write_text(original)
        data = installer.prepare_settings(self.path, self.script)
        installer.atomic_write(self.path, data)
        installer.atomic_write(self.path, data)
        backups = list(self.path.parent.glob('settings.boathouse-backup-*.json'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), original)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
