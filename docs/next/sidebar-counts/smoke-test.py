from pathlib import Path
import json, os, shlex, socket, subprocess, tempfile, time

binary = os.environ.get('HERDR_COUNTS_TEST_BIN', str(Path(__file__).resolve().parents[3] / 'target/release/herdr'))
artifacts = Path(os.environ.get('HERDR_COUNTS_ARTIFACTS', tempfile.mkdtemp(prefix='herdr-counts-artifacts-')))
root = Path(tempfile.mkdtemp(prefix='herdr-sidebar-counts-'))
config = root/'config/herdr/config.toml'
config.parent.mkdir(parents=True)
base_config = 'onboarding = false\n[ui.sound]\nenabled = false\n'
config.write_text(base_config)
env = {k:v for k,v in os.environ.items() if not k.startswith('HERDR_')}
env.update(XDG_CONFIG_HOME=str(root/'config'), XDG_STATE_HOME=str(root/'state'), XDG_DATA_HOME=str(root/'data'), SHELL='/bin/sh')
name = 'counts-smoke'
tmux_socket = f'herdr-counts-{os.getpid()}'
api_socket = root/'config/herdr/sessions'/name/'herdr.sock'

def run(*args, check=True):
    return subprocess.run(args, env=env, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check, timeout=15)

def cli(*args):
    return run(binary, '--session', name, *args)

def capture():
    return run('tmux', '-L', tmux_socket, 'capture-pane', '-p', '-t', 'smoke').stdout

def wait_frame(label, predicate):
    deadline = time.monotonic()+15
    last = ''
    while time.monotonic()<deadline:
        last = capture()
        if predicate(last):
            (artifacts/f'smoke-{label}.txt').write_text(last)
            print(label, 'PASS', flush=True)
            return last
        time.sleep(0.15)
    (artifacts/f'smoke-{label}-FAILED.txt').write_text(last)
    raise AssertionError(f'{label}: expected header did not appear:\n{last}')

def api(method, params):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(5)
        s.connect(str(api_socket))
        s.sendall(json.dumps({'id':'counts-smoke', 'method':method, 'params':params}).encode()+b'\n')
        with s.makefile('rb') as f:
            reply = json.loads(f.readline())
        assert 'error' not in reply, reply
        return reply

def reload_counts(enabled):
    value = 'true' if enabled else 'false'
    config.write_text(base_config+f'[ui.sidebar.spaces]\nshow_count = {value}\n[ui.sidebar.agents]\nshow_count = {value}\n')
    run('tmux', '-L', tmux_socket, 'send-keys', '-t', 'smoke', 'C-b', 'R')

try:
    run('tmux', '-L', tmux_socket, 'new-session', '-d', '-s', 'smoke', '-x', '106', '-y', '30', 'exec '+shlex.quote(binary)+' --session '+name)
    wait_frame('defaults', lambda t: 'spaces (1)' in t and 'agents (0)' in t)
    initial = json.loads(cli('workspace','list').stdout)['result']['workspaces'][0]['workspace_id']
    cli('workspace','rename',initial,'Demo workspace')
    added = json.loads(cli('workspace','create','--cwd',str(root),'--label','Sample agent','--no-focus').stdout)['result']
    api('pane.report_agent', {'pane_id':added['root_pane']['pane_id'], 'source':'sidebar-count-smoke', 'agent':'pi', 'state':'working', 'seq':1})
    wait_frame('added', lambda t: 'spaces (2)' in t and 'agents (1)' in t)
    reload_counts(False)
    wait_frame('demo-before', lambda t: 'Sample agent' in t and 'spaces (' not in t and 'agents (' not in t)
    reload_counts(True)
    wait_frame('demo-after', lambda t: 'spaces (2)' in t and 'agents (1)' in t)
    cli('workspace','close',added['workspace']['workspace_id'])
    wait_frame('removed', lambda t: 'spaces (1)' in t and 'agents (0)' in t)
    reload_counts(False)
    wait_frame('off', lambda t: ' spaces' in t and ' agents' in t and 'spaces (' not in t and 'agents (' not in t)
    reload_counts(True)
    wait_frame('on', lambda t: 'spaces (1)' in t and 'agents (0)' in t)
    (artifacts/'smoke-result.json').write_text(json.dumps({'passed':True,'isolated_root':str(root),'tests':['defaults','added','demo-before','demo-after','removed','off','on']},indent=2)+'\n')
finally:
    if api_socket.exists():
        run(binary, '--session', name, 'server', 'stop', check=False)
    run('tmux','-L',tmux_socket,'kill-server',check=False)

print('Terminal captures:', artifacts)
