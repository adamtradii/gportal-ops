#!/usr/bin/env python3
"""Test double for lftp: runs the REAL lftp against a local directory (file:// backend) and injects the
FTP-side failures seen in the 2026-10-27 incident. Used only by scripts/test_tfg_ftp.py.
  FAKE_STATE   json file with counters
  FAKE_FAIL    {"remote/path": n}  the first n puts of that path fail with a 550 and are skipped
  FAKE_NOWIPE  ["dir", ...]        'rm -rf dir' (and rm of its entries) silently does nothing
  FAKE_GETERR  ["path", ...]       'get path' fails with a network error instead of 550
  FAKE_EXISTS_ERR  1               a put onto an existing remote file fails like 'put -c' did (size increased)
"""
import json, os, shlex, subprocess, sys

root = sys.argv[-1]
base = root[len('file://'):]
fail = json.loads(os.environ.get('FAKE_FAIL', '{}'))
nowipe = json.loads(os.environ.get('FAKE_NOWIPE', '[]'))
geterr = json.loads(os.environ.get('FAKE_GETERR', '[]'))
state_p = os.environ.get('FAKE_STATE', os.path.join(base, '..', 'fake_state.json'))
state = json.load(open(state_p)) if os.path.exists(state_p) else {}
msgs, keep, last_injected = [], [], False
for line in sys.stdin.read().splitlines():
    if not line.strip():
        continue
    w = shlex.split(line)
    cmd, injected = w[0], False
    if cmd == 'put':
        local, rel = w[1], w[w.index('-o') + 1]
        if os.environ.get('FAKE_EXISTS_ERR') and os.path.exists(os.path.join(base, rel)) and '-c' in w:
            msgs.append('put: %s: file size increased during transfer' % local); injected = True
        elif state.get(rel, 0) < fail.get(rel, 0):
            state[rel] = state.get(rel, 0) + 1
            msgs.append('put: Access failed: 550 Permission denied (%s)' % rel); injected = True
    elif cmd == 'rm' and any(x.startswith('-') and 'r' in x for x in w[1:]):
        tgt = [x for x in w[1:] if not x.startswith('-')][0]
        if tgt.split('/')[0] in nowipe:
            injected = False
            continue
    elif cmd == 'get':
        rem = w[1]
        if rem in geterr:
            msgs.append('get: Fatal error: Max-retries exceeded'); injected = True
    last_injected = injected
    if not injected:
        keep.append(line)
p = subprocess.run(['lftp', root], input='\n'.join(keep) + '\n', capture_output=True, text=True)
sys.stdout.write(p.stdout)
sys.stderr.write(p.stderr + '\n'.join(msgs) + ('\n' if msgs else ''))
json.dump(state, open(state_p, 'w'))
sys.exit(1 if last_injected else p.returncode)
