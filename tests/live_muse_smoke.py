"""Read-only live stdio smoke test; optionally verify the zero-credit deploy gate.

python3 tests/live_muse_smoke.py --workspace YOUR_QA_WORKSPACE
Only use --verify-unfunded-deploy against a dedicated empty, unfunded QA workspace.
No top-up, domain purchase, invitation or balance adjustment is performed.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--verify-unfunded-deploy", action="store_true")
    args = parser.parse_args()
    child = subprocess.Popen([sys.executable, str(ROOT / "skills/boathouse/scripts/mcp_bridge.py")],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ident = 0

    def rpc(method, params):
        nonlocal ident
        ident += 1
        child.stdin.write(json.dumps({"jsonrpc":"2.0","id":ident,"method":method,"params":params})+'\n')
        child.stdin.flush()
        response = json.loads(child.stdout.readline())
        assert response.get('id') == ident and 'error' not in response, 'Invalid RPC response'
        return response['result']

    def tool(name, **kw):
        return rpc('tools/call',{'name':name,'arguments':{'workspace':args.workspace,**kw}})

    report = {}
    try:
        init = rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},
                                'clientInfo':{'name':'boathouse-muse-smoke','version':'1.1.0'}})
        report['initialize'] = init['serverInfo']['name']=='boathouse'
        catalog = rpc('tools/list',{})['tools']
        report['tool_count'] = len(catalog)
        assert {'whoami','deploy','share','domain_buy'} <= {x['name'] for x in catalog}
        identity = tool('whoami')
        assert not identity.get('isError'), 'Connection could not be authenticated'
        report['selected_workspace_matches'] = identity['structuredContent']['workspace']==args.workspace
        assert report['selected_workspace_matches']
        before = tool('list_tools')
        assert not before.get('isError')
        for name in ['billing','prices']:
            result = tool(name)
            report[name] = not result.get('isError')
            assert report[name], name+' failed'
        items = before['structuredContent']['items']
        if items:
            report['usage'] = not tool('usage', tool=items[0]['slug']).get('isError')
            assert report['usage']
        else:
            report['usage'] = 'not applicable: workspace has no apps'
        if args.verify_unfunded_deploy:
            assert identity['structuredContent']['balance_cents']==0, 'QA balance must be zero'
            assert before['structuredContent']['items']==[], 'QA workspace must be empty'
            result = tool('deploy',tool='muse-unfunded-check',files={'index.html':'<!doctype html><title>Muse QA</title><p>Disposable connector check.</p>'})
            assert result.get('isError'), 'Unfunded deployment was unexpectedly allowed'
            report['unfunded_deploy_blocked'] = '402' in json.dumps(result) and 'balance' in json.dumps(result).lower()
            assert report['unfunded_deploy_blocked']
            after = tool('list_tools')
            assert after['structuredContent']['items']==[], 'Unfunded test unexpectedly created a tool'
            report['no_tool_created'] = True
            report['balance_unchanged'] = tool('whoami')['structuredContent']['balance_cents']==0
            assert report['balance_unchanged']
        print(json.dumps(report,indent=2))
    finally:
        child.stdin.close()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


if __name__=='__main__':
    main()
