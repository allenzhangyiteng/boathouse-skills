#!/usr/bin/env python3
"""Credential-local stdio adapter for Boat House's existing remote MCP service.

Python 3.9+, standard library only. No credentials in plugin manifests, stdout,
URLs or command arguments. No retries of mutations and no HTTP redirects.
"""
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

API = "https://api.boathousecloud.com"
ENDPOINT = "https://mcp.boathousecloud.com/mcp"
MAX_MESSAGE = 64 * 1024 * 1024
# Audited read-only operations. Unknown/new tools keep the conservative default.
READ_ONLY = frozenset({"whoami", "list_tools", "get_tool", "pull", "logs", "releases",
                       "access_requests", "secrets_list", "users_list", "domains_list",
                       "domain_renewals", "domain_dns", "usage", "billing", "prices"})
CONNECT = ("Connect Boat House first: open https://boathousecloud.com/account, "
           "use Copy connection, and let your agent redeem that one-time code. "
           "Never paste a raw API key or print your credential file.")


class ConnectionProblem(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ConnectionProblem("Boat House redirected the request; no credentials were forwarded. Check service status.")


def read_config():
    if os.environ.get("BH_CONFIG"):
        candidates = [Path(os.environ["BH_CONFIG"]).expanduser()]
    else:
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        candidates = [config_home / "boathouse/config.json", Path.home() / ".boathouse/config.json"]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        raise ConnectionProblem(CONNECT)
    try:
        with path.open("rb") as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError()
        cfg = json.loads(raw)
        if not isinstance(cfg, dict):
            raise ValueError()
        if "logins" not in cfg:
            cfg = {"logins": [cfg], "default": cfg.get("workspace")}
        if not isinstance(cfg["logins"], list) or not all(isinstance(x, dict) for x in cfg["logins"]):
            raise ValueError()
        return cfg
    except (OSError, ValueError, TypeError):
        raise ConnectionProblem("The local Boat House connection is unreadable. " + CONNECT) from None


def requested_workspace(message):
    params = message.get("params", {})
    args = params.get("arguments", {}) if isinstance(params, dict) else {}
    if not isinstance(args, dict):
        raise ConnectionProblem("Tool arguments must be an object.")
    workspace = args.get("workspace")
    tool = args.get("tool")
    if isinstance(tool, str) and "/" in tool:
        prefix = tool.split("/", 1)[0]
        if workspace is not None and workspace != prefix:
            raise ConnectionProblem("The tool and workspace select different organizations. Use one matching workspace.")
        workspace = prefix
    if workspace is not None and (not isinstance(workspace, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", workspace)):
        raise ConnectionProblem("Select an organization using its workspace short name.")
    return workspace


def connection(message):
    selected = requested_workspace(message)
    if os.environ.get("BH_KEY"):
        login = {"api": os.environ.get("BH_API", API), "key": os.environ["BH_KEY"]}
    else:
        cfg = read_config()
        selected = selected or cfg.get("default")
        logins = cfg["logins"]
        exact = [x for x in logins if selected and x.get("workspace") == selected]
        accounts = [x for x in logins if x.get("workspace") == "*"]
        choices = exact or accounts or (logins if not selected else [])
        if len(choices) != 1:
            raise ConnectionProblem("No single Boat House connection matches this organization. "
                                    "Check bh whoami and explicitly select the workspace; do not guess an account.")
        login = choices[0]
        selected = selected or login.get("workspace")
    if selected == "*":
        selected = None
    if selected is not None and (not isinstance(selected, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", selected)):
        raise ConnectionProblem("The saved organization is invalid. Select it again with bh use.")
    if str(login.get("api", "")).rstrip("/") != API:
        raise ConnectionProblem("This adapter connects only to boathousecloud.com. "
                                "Use your self-hosted server's own MCP connection settings; its key was not sent.")
    key = login.get("key")
    if not isinstance(key, str) or not re.fullmatch(r"[!-~]{1,2048}", key):
        raise ConnectionProblem(CONNECT)
    headers = {"Authorization": "Bearer " + key}
    if selected:
        headers["Boathouse-Workspace"] = selected
    return headers, key


def rpc_error(ident, code, message):
    return {"jsonrpc": "2.0", "id": ident, "error": {"code": code, "message": message}}


def failure(message, detail):
    if message.get("method") == "tools/call":
        return {"jsonrpc": "2.0", "id": message["id"], "result": {
            "isError": True, "content": [{"type": "text", "text": detail}]}}
    return rpc_error(message.get("id"), -32603, detail)


def forward(message, opener=None):
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return rpc_error(None, -32600, "Expected a JSON-RPC 2.0 request.")
    if "id" not in message:  # Boat House has no server-side session or notification work.
        return None
    if message.get("params") is not None and not isinstance(message["params"], dict):
        return rpc_error(message["id"], -32602, "params must be an object.")
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
               "MCP-Protocol-Version": "2025-03-26", "User-Agent": "boathouse-muse/1.1.0"}
    key = None
    try:
        if message["method"] == "tools/call":
            auth, key = connection(message)
            headers.update(auth)
        opener = opener or build_opener(ProxyHandler({}), NoRedirect())
        request = Request(ENDPOINT, data=json.dumps(message).encode(), headers=headers, method="POST")
        with opener.open(request, timeout=300 if message["method"] == "tools/call" else 25) as response:
            raw = response.read(MAX_MESSAGE + 1)
        if len(raw) > MAX_MESSAGE:
            raise ConnectionProblem("The response is too large. Use the Boat House CLI to export large files.")
        if key:
            raw = raw.replace(key.encode(), b"[REDACTED]")
        result = json.loads(raw)
        if not isinstance(result, dict) or result.get("jsonrpc") != "2.0" or result.get("id") != message["id"]:
            raise ConnectionProblem("Boat House returned an invalid MCP response. Check service status before retrying.")
        if message["method"] == "tools/list":
            for tool in result.get("result", {}).get("tools", []):
                readonly = tool.get("name") in READ_ONLY
                tool["annotations"] = {**tool.get("annotations", {}), "readOnlyHint": readonly,
                                       "destructiveHint": not readonly}
        if message["method"] == "initialize" and isinstance(result.get("result"), dict):
            result["result"]["instructions"] = (
                "Boat House hosts and shares small apps. This local adapter authenticates with the existing bh connection. "
                "If not connected, follow the Boat House skill and Copy connection from https://boathousecloud.com/account. "
                "Never ask for or print API keys. Call whoami to verify the organization; specify workspace on calls. "
                "Confirm spending, public access and invitations with the user. Use the CLI for local folder deployment; "
                "the remote MCP server cannot read local file paths. Tool permissions and prices are enforced by Boat House."
            )
        return result
    except ConnectionProblem as exc:
        return failure(message, str(exc))
    except HTTPError as exc:
        detail = CONNECT if exc.code in (401, 403) else f"Boat House returned HTTP {exc.code}. Check service status."
        return failure(message, detail)
    except (URLError, OSError, TimeoutError):
        return failure(message, "Could not reach Boat House. No automatic retry was made. "
                       "For a change or purchase, check its status before retrying; it may have completed.")
    except (ValueError, TypeError, KeyError):
        return failure(message, "Boat House returned an invalid response. Check service status before retrying.")


def main():
    while True:
        line = sys.stdin.buffer.readline(MAX_MESSAGE + 1)
        if not line:
            return
        if len(line) > MAX_MESSAGE:
            reply = rpc_error(None, -32600, "Request too large; use the CLI for large deployments.")
            print(json.dumps(reply), flush=True)
            return
        if not line.strip():
            continue
        try:
            reply = forward(json.loads(line))
        except (ValueError, UnicodeError):
            reply = rpc_error(None, -32700, "Invalid JSON.")
        if reply is not None:
            print(json.dumps(reply, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    try:
        main()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
