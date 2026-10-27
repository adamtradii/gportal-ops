#!/usr/bin/env python3
"""FTP half of .github/workflows/tfg-update.yml (everything that touches the G-Portal server).

Why this is a script and not workflow YAML: it can be tested locally (scripts/test_tfg_ftp.py runs it against
a throw-away directory through the real lftp binary), and every step shares one definition of "present",
"absent" and "failed".

Facts this is built around (all read out of the failed runs 40356210574 and 40530320802, 2026-10-26/27):
  * lftp's exit status is the status of the LAST command only. A chunk with five failed puts followed by a
    successful one exits 0, so "chunk done (try 1)" proved nothing. We read lftp's own error lines instead.
  * 'put -c' onto a file that already exists in full ends in "put: <file>: file size increased during
    transfer" (seen for files that were uploaded complete one try earlier). On a smaller remote file it
    RESUMES, i.e. appends the tail of the new file to the old one. We never use 'put -c' on pack files.
  * G-Portal FTP has no NLST. 'get' on a missing path answers "550 path does not exists (<path>)" and that is
    the only existence probe used for decisions. 'cls -1 <dir>' (LIST based) is used where it works and its
    absence is never fatal.
  * A transient failure must never be read as "file absent" (the old code wrote server.properties from an
    empty file when a get failed for network reasons, and treated an unreadable version marker as "none",
    which reinstalls the whole pack).

Environment: HOST PORT FUSER FPASS (secrets), DRY_RUN=true (read-only: print plans, change nothing),
WIPE_WORLD, KEEP_FILES, LATEST, SLEEP (seconds between retries, default 10), LFTP_CMD (JSON argv, tests only).
Subcommands: current | release | save | wipe | upload | fixes | restore | marker
"""
import filecmp
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.request

DRY = os.environ.get('DRY_RUN', '').strip().lower() == 'true'
SLEEP = float(os.environ.get('SLEEP', '10'))
WIPE_DIRS = ['mods', 'config', 'kubejs', 'defaultconfigs', 'scripts', 'tacz', 'patchouli_books']
WORLD_DIRS = ['world', 'world_nether', 'world_the_end']
PRELUDE = ('set ftp:ssl-allow yes\nset ftp:use-site-chmod no\nset net:max-retries 6\n'
           'set net:reconnect-interval-base 5\nset net:timeout 40\n')
ABSENT = re.compile(r'(?i)does not exist|no such file|not found')
FATAL = re.compile(r'(?i)fatal error|login (failed|incorrect)|max-retries|connection refused|not connected')
CHUNK_BYTES = 120 * 1024 * 1024
FIXES = [  # (file, "key=value") - the same fixes the workflow has always re-applied, see CLAUDE.md
    ('config/modernfix-mixins.properties', 'mixin.perf.clear_mixin_classinfo=false'),
    # Simple Voice Chat must NOT use its default UDP 24454 (taken on the shared G-Portal host; the bind failure
    # shuts the whole server down ~1 s after load). -1 = share the game port; query must then be OFF.
    ('config/voicechat/voicechat-server.properties', 'port=-1'),
    ('server.properties', 'enable-query=false'),
    ('server.properties', 'enable-rcon=true'),
    # TFC worldgen: must be set before the first boot creates the world. Appended last so it wins.
    ('server.properties', 'level-type=tfc:overworld'),
    # A fresh G-Portal reinstall ships no eula.txt; without it the host never launches Java.
    ('eula.txt', 'eula=true'),
]


# ---------------------------------------------------------------- plumbing
def say(msg=''):
    print(msg, flush=True)


def gha(level, msg):
    print('::%s::%s' % (level, msg), flush=True)


def summary(text):
    p = os.environ.get('GITHUB_STEP_SUMMARY')
    if p:
        with open(p, 'a') as f:
            f.write(text + '\n')


def q(s):
    """lftp double-quoted word."""
    return '"%s"' % s.replace('\\', '\\\\').replace('"', '\\"')


def lftp_argv():
    if os.environ.get('LFTP_CMD'):
        return json.loads(os.environ['LFTP_CMD'])
    return ['lftp', '-p', os.environ.get('PORT') or '21', '-u',
            '%s,%s' % (os.environ.get('FUSER', ''), os.environ.get('FPASS', '')), os.environ['HOST']]


def redact(line):
    for s in (os.environ.get('FPASS'), os.environ.get('HOST')):
        if s and len(s) > 3:
            line = line.replace(s, '***')
    return line


def run_lftp(script, timeout=3600):
    """Run one lftp session; returns (exit status, output lines). The status is lftp's: LAST command only."""
    try:
        p = subprocess.run(lftp_argv(), input=script, capture_output=True, text=True,
                           errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, ['lftp: session timed out after %ds' % timeout]
    out = (p.stdout or '') + (p.stderr or '')
    return p.returncode, [redact(l) for l in out.splitlines() if l.strip()]


def nap():
    if SLEEP:
        time.sleep(SLEEP)


def fetch(remote, local, tries=3):
    """Download one file. Returns 'ok' | 'absent' | 'error' (never confuses a network fault with absence)."""
    out = []
    for i in range(tries):
        if os.path.exists(local):
            os.remove(local)
        os.makedirs(os.path.dirname(local) or '.', exist_ok=True)
        rc, out = run_lftp(PRELUDE + 'get %s -o %s\nbye\n' % (q(remote), q(local)), 900)
        if rc == 0 and os.path.exists(local):
            return 'ok', out
        if os.path.exists(local):
            os.remove(local)
        if any(ABSENT.search(l) for l in out):
            return 'absent', out
        say('get %s: try %d failed (%s)' % (remote, i + 1, ' | '.join(out[-2:]) or 'rc=%s' % rc))
        if i < tries - 1:
            nap()
    return 'error', out


def listing(path):
    """Best effort 'cls -1': list of entry names under path, [] when empty or absent, None when it cannot say."""
    rc, out = run_lftp(PRELUDE + 'cls -1 %s\nbye\n' % q(path), 300)
    if rc != 0:
        return [] if any(ABSENT.search(l) for l in out) else None
    pre = path.rstrip('/') + '/'
    names = []
    for l in out:
        l = l.strip()
        if l.startswith(pre):
            l = l[len(pre):]
        l = l.rstrip('/')
        if l and l not in ('.', '..'):
            names.append(l)
    return names


def read_keep(path='keep/.saved'):
    if not os.path.exists(path):
        return []
    return [l.rstrip('\n') for l in open(path) if l.strip()]


# ---------------------------------------------------------------- release choice (pure, unit tested)
def pick_release(rels, vmatch=''):
    rels = [r for r in rels if not r.get('draft') and not r.get('prerelease')]
    v = (vmatch or '').strip()
    if v:
        if re.fullmatch(r'v?[0-9]+(\.[0-9]+)+', v):          # a plain version means exactly that tag
            want = v.lstrip('v')
            rels = [r for r in rels if r.get('tag_name', '').lstrip('v') == want]
        else:
            rels = [r for r in rels if re.search(v, r.get('tag_name', ''))]
    if not rels:
        raise SystemExit('no matching TFG release found for version_match=%r' % v)
    r = rels[0]
    zips = [a for a in r.get('assets', []) if re.search(r'(?i)server', a['name']) and a['name'].endswith('.zip')]
    zips.sort(key=lambda a: 'serverpack' not in a['name'].lower())
    if not zips:
        raise SystemExit('release %s has no server zip; assets: %s'
                         % (r['tag_name'], ', '.join(a['name'] for a in r.get('assets', []))))
    return r, zips[0]


def cmd_release():
    h = {'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json',
         'User-Agent': 'tfg-auto-update'}
    url = 'https://api.github.com/repos/TerraFirmaGreg-Team/Modpack-Modern/releases?per_page=100'
    rels = None
    for i in range(4):
        try:
            rels = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60))
            break
        except Exception as e:  # rate limit, 5xx, DNS: retry, then fail BEFORE anything destructive
            say('release lookup try %d failed: %s' % (i + 1, e))
            time.sleep(5 * (i + 1) if SLEEP else 0)
    if rels is None:
        raise SystemExit('could not read the TFG release list; nothing was changed')
    try:
        r, asset = pick_release(rels, os.environ.get('VMATCH', ''))
    except SystemExit as e:
        say('available tags: ' + ', '.join(x.get('tag_name', '?') for x in rels[:20]))
        raise e
    open('latest.txt', 'w').write(r['tag_name'])
    open('asset_url.txt', 'w').write(asset['browser_download_url'])
    open('release_url.txt', 'w').write(r['html_url'])
    say('latest release: %s %s' % (r['tag_name'], asset['name']))
    return 0


def cmd_current():
    st, out = fetch('.tfg-version', 'current.txt')
    if st == 'error':
        gha('error', 'cannot read .tfg-version (network, not "missing"): %s. Nothing was changed; '
                     're-run later. NOT treating this as "no version" because that would reinstall the pack.'
            % ' | '.join(out[-2:]))
        return 3
    cur = open('current.txt').read().strip() if st == 'ok' else 'none'
    open('current.txt', 'w').write(cur or 'none')
    say('current version marker: %s' % (cur or 'none'))
    return 0


# ---------------------------------------------------------------- save
def valid_keep(p):
    return bool(p) and not p.startswith('/') and '..' not in p.split('/') and not p.startswith('#')


def cmd_save():
    os.makedirs('keep', exist_ok=True)
    extra = []
    st, out = fetch('.keep-files', 'keep/.list')
    if st == 'error':
        gha('error', 'cannot read the server\'s .keep-files (network). Nothing was deleted; re-run.')
        return 1
    if st == 'ok':
        extra = [l.strip() for l in open('keep/.list', errors='replace').read().replace('\r', '').split('\n')
                 if l.strip() and not l.strip().startswith('#')]
    names = sorted({p for p in os.environ.get('KEEP_FILES', '').split() + extra if valid_keep(p)})
    saved = []
    for f in names:
        st, out = fetch(f, 'keep/' + f)
        if st == 'ok' and os.path.getsize('keep/' + f) > 0:
            say('saved %s (%d bytes)' % (f, os.path.getsize('keep/' + f)))
            saved.append(f)
        elif st == 'absent':
            gha('warning', '%s is not on the server, nothing to keep' % f)
        else:
            gha('error', 'could not read %s (%s). Nothing was deleted; re-run, the wipe must not start '
                         'without a safe copy.' % (f, st))
            return 1
    open('keep/.saved', 'w').write(''.join(f + '\n' for f in saved))
    say('%d file(s) kept for the put-back' % len(saved))
    return 0


# ---------------------------------------------------------------- wipe
def staged_samples(d, n=3, max_bytes=2 * 1024 * 1024):
    out = []
    for dp, _, fns in os.walk(os.path.join('stage', d)):
        for fn in fns:
            fp = os.path.join(dp, fn)
            if os.path.getsize(fp) <= max_bytes:
                out.append((os.path.getsize(fp), os.path.relpath(fp, 'stage').replace(os.sep, '/')))
    return [rel for _, rel in sorted(out)[:n]]


def leftovers(d):
    """Names still on the server under d. Uses the listing when it works, else get-probes of staged files."""
    names = listing(d)
    if names is not None:
        return ['%s/%s' % (d, n) for n in names], 'listing'
    left = []
    for rel in staged_samples(d):
        st, _ = fetch(rel, 'probe.tmp', tries=2)
        if st != 'absent':
            left.append(rel)
    if os.path.exists('probe.tmp'):
        os.remove('probe.tmp')
    return left, 'probe'


def cmd_wipe():
    dirs = WIPE_DIRS + (WORLD_DIRS if os.environ.get('WIPE_WORLD', '').strip().lower() == 'true' else [])
    say('%s: rm -rf %s' % ('WOULD DELETE (dry run)' if DRY else 'deleting', ' '.join(dirs)))
    if os.environ.get('WIPE_WORLD', '').strip().lower() == 'true':
        gha('warning', 'wipe_world=true: the world folders are deleted too')
    pending = {d: None for d in dirs}                       # dir -> specific leftovers from the last look
    for rnd in range(1, 4):
        if not pending:
            break
        say('--- wipe pass %d: %s' % (rnd, ' '.join(pending)))
        for d, entries in list(pending.items()):
            if DRY:
                continue
            script = PRELUDE
            if entries:                                      # pass 2+: the dir survived; take its entries one by one
                script += ''.join('rm -rf %s\n' % q(e) for e in entries)
            script += 'rm -rf %s\nbye\n' % q(d)
            t0 = time.time()
            rc, out = run_lftp(script, 3600)
            say('%s: rc=%s %.0fs %s' % (d, rc, time.time() - t0, ' | '.join(out[-3:])))
        nxt = {}
        for d in pending:
            left, how = leftovers(d)
            if left:
                say('%s: %d left over (%s): %s' % (d, len(left), how, ', '.join(left[:8])))
                nxt[d] = left if how == 'listing' else None
            else:
                say('%s: gone (%s)' % (d, how))
        if DRY:
            say('DRY RUN: %d of %d pack folder(s) currently have content on the server: %s' % (
                len(nxt), len(pending), ', '.join(nxt) or 'none'))
            return 0
        pending = nxt
        if pending:
            nap()
    if pending:
        msg = ('wipe left old files in: %s. The upload overwrites every pack file by exact name, so this is not '
               'fatal, but jars that only exist in the OLD pack would stay and can crash the boot (duplicate mods).'
               % ', '.join(pending))
        gha('warning' if not DRY else 'notice', msg)
        summary('- WIPE INCOMPLETE: ' + ', '.join(pending))
    return 0


# ---------------------------------------------------------------- upload
def build_chunks():
    chunks, cur, cur_bytes = [], [], 0
    for dp, dns, fns in os.walk('stage'):
        dns.sort()
        for fn in sorted(fns):
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, 'stage').replace(os.sep, '/')
            size = os.path.getsize(full)
            if cur and cur_bytes + size > CHUNK_BYTES:
                chunks.append(cur)
                cur, cur_bytes = [], 0
            cur.append((full, rel, size))
            cur_bytes += size
    if cur:
        chunks.append(cur)
    return chunks


def chunk_script(files):
    s, dirs = PRELUDE, set()
    for full, rel, _ in files:
        d = os.path.dirname(rel)
        if d and d not in dirs:
            parts = d.split('/')
            for k in range(1, len(parts) + 1):
                p = '/'.join(parts[:k])
                if p not in dirs:
                    s += 'mkdir -pf %s\n' % q(p)
                    dirs.add(p)
        # Delete by exact name, then a PLAIN put (never 'put -c': it resumes onto a same-named remote file).
        # lftp itself reconnects and continues a transfer that drops inside one put.
        s += 'rm -f %s\nput %s -o %s\n' % (q(rel), q(full), q(rel))
    return s


def parse_failures(out, rc, files):
    """(set of rel paths that failed, True when the whole batch must be redone)."""
    failed, unmapped = set(), False
    for l in out:
        if not (l.startswith('put: ') or FATAL.search(l)):
            continue
        hit = [rel for full, rel, _ in files if (full + ':') in l or ('(%s)' % rel) in l]
        if hit:
            failed.update(hit)
        else:
            unmapped = True
    if rc != 0 and files and files[-1][1] not in failed:
        unmapped = True                                        # the last put failed and said nothing we can map
    return failed, unmapped


def sample_for_verify(chunks):
    pick, small = {}, []
    for ch in chunks:
        fit = [f for f in ch if f[2] <= 8 * 1024 * 1024] or sorted(ch, key=lambda f: f[2])[:1]
        pick[fit[-1][1]] = fit[-1]
        small += [f for f in ch if f[2] <= 1024 * 1024]
    for f in (f for ch in chunks for f in ch if '/' not in f[1]):   # top-level files were the ones never wiped
        pick[f[1]] = f
    rnd = random.Random(len(small))
    for f in rnd.sample(small, min(20, len(small))):
        pick[f[1]] = f
    return list(pick.values())


def cmd_upload():
    chunks = build_chunks()
    os.makedirs('chunks', exist_ok=True)
    for i, ch in enumerate(chunks):
        open('chunks/%04d.lftp' % i, 'w').write(chunk_script(ch))
    total = sum(len(c) for c in chunks)
    say('generated %d chunks, %d files, %d MB' % (len(chunks), total, sum(f[2] for c in chunks for f in c) >> 20))
    if DRY:
        for i, ch in enumerate(chunks):
            lines = chunk_script(ch).splitlines()
            say('--- chunks/%04d.lftp: %d files, %d MB, %d script lines; first lines:' % (i, len(ch), sum(f[2] for f in ch) >> 20, len(lines)))
            for l in lines[:9]:
                say('    ' + l)
            if any(l.startswith('put -c') for l in lines):
                gha('error', 'BUG: put -c in a generated script')
                return 1
        say('--- verify sample would be: ' + ', '.join(f[1] for f in sample_for_verify(chunks))[:600])
        say('DRY RUN: nothing uploaded')
        return 0
    failed = {}
    for i, ch in enumerate(chunks):
        pending, ok = ch, False
        for attempt in (1, 2, 3):
            t0 = time.time()
            rc, out = run_lftp(chunk_script(pending), 3600)
            bad, whole = parse_failures(out, rc, pending)
            say('chunk %04d attempt %d: %d file(s), %.0fs, rc=%s, %s' % (
                i, attempt, len(pending), time.time() - t0, rc, 'OK' if not (bad or whole) else '%d failed%s' % (
                    len(bad), ' + unmapped error' if whole else '')))
            for l in out[:12]:
                say('    ' + l)
            if not bad and not whole:
                ok = True
                break
            if not whole:
                pending = [f for f in pending if f[1] in bad]
            if attempt < 3:
                nap()
        if not ok:
            for f in pending:
                failed[f[1]] = 'chunk %04d failed 3 tries' % i
            gha('error', 'chunk %04d FAILED after 3 tries; failed files (%d): %s' % (
                i, len(pending), ', '.join(f[1] for f in pending[:25])))
            say('continuing with the next chunk so the put-back and fixes can still run')
    # Verify by reading back a sample (no listing exists on this FTP): last file of each chunk, top-level files, 20 small ones.
    say('--- read-back verify')
    for full, rel, size in sample_for_verify(chunks):
        if rel in failed:
            continue
        st, out = fetch(rel, 'verify.tmp', tries=2)
        if st != 'ok' or not filecmp.cmp(full, 'verify.tmp', shallow=False):
            failed[rel] = 'read-back %s' % ('missing' if st == 'absent' else 'unreadable' if st == 'error' else 'differs')
            say('VERIFY FAIL %s: %s' % (rel, failed[rel]))
    if os.path.exists('verify.tmp'):
        os.remove('verify.tmp')
    open('upload-failed.txt', 'w').write(''.join('%s\t%s\n' % kv for kv in sorted(failed.items())))
    if failed:
        gha('error', '%d file(s) did not upload: %s' % (len(failed), ', '.join(sorted(failed)[:25])))
        summary('## UPLOAD INCOMPLETE: %d file(s)\n%s\n\nNext steps: the pack is partly installed. Re-run '
                '"TFG auto-update" with force=true (safe to repeat: every file is overwritten by exact name), '
                'or put the listed files by hand with server-file.yml. Do not trust a restart until it is green.\n'
                % (len(failed), '\n'.join('- `%s` (%s)' % kv for kv in sorted(failed.items())[:60])))
        return 1
    say('upload complete: %d files, sample verified' % total)
    return 0


# ---------------------------------------------------------------- put-back helpers
def put_verified(local, remote, tries=4):
    """rm by exact name, plain put, read back, compare. True when the server copy equals local."""
    for i in range(tries):
        d = os.path.dirname(remote)
        rc, out = run_lftp(PRELUDE + ('mkdir -pf %s\n' % q(d) if d else '') + 'rm -f %s\nput %s -o %s\nbye\n' % (
            q(remote), q(local), q(remote)), 900)
        st, _ = fetch(remote, 'back.tmp', tries=2)
        if st == 'ok' and filecmp.cmp(local, 'back.tmp', shallow=False):
            os.remove('back.tmp')
            return True
        say('%s: try %d did not verify (%s)' % (remote, i + 1, ' | '.join(out[-2:])))
        nap()
    if os.path.exists('back.tmp'):
        os.remove('back.tmp')
    return False


def cmd_fixes():
    bad = 0
    byfile = {}
    for f, line in FIXES:
        byfile.setdefault(f, []).append(line)
    for f, lines in byfile.items():
        st, out = fetch(f, 'fix.tmp')
        if st == 'error':                                    # never write a file we could not read
            gha('error', 'fix skipped, could not read %s (%s)' % (f, ' | '.join(out[-1:])))
            bad += 1
            continue
        text = open('fix.tmp', errors='replace').read() if st == 'ok' else ''
        cur = text.replace('\r\n', '\n').split('\n')
        if cur and cur[-1] == '':
            cur.pop()
        new = list(cur)
        for line in lines:
            if line not in new:
                key = line.split('=', 1)[0] + '='
                new = [l for l in new if not l.startswith(key)] + [line]
        if new == cur and st == 'ok':
            say('%s: already correct (%s)' % (f, ', '.join(lines)))
            continue
        open('fix.tmp', 'w', newline='\n').write('\n'.join(new) + '\n')
        if DRY:
            say('WOULD PATCH %s: %s (file %s)' % (f, ', '.join(lines), 'present' if st == 'ok' else 'missing, would be created'))
            continue
        if put_verified('fix.tmp', f):
            say('PASS patched %s: %s' % (f, ', '.join(lines)))
        else:
            gha('error', '%s could not be patched/verified' % f)
            bad += 1
    if os.path.exists('fix.tmp'):
        os.remove('fix.tmp')
    return 1 if bad else 0


def cmd_restore():
    files = read_keep()
    if not files:
        say('nothing was saved, nothing to put back')
        return 0
    bad = 0
    for f in files:
        if DRY:
            say('WOULD PUT BACK %s (%d bytes)' % (f, os.path.getsize('keep/' + f)))
        elif put_verified('keep/' + f, f, tries=5):
            say('PASS restored %s' % f)
        else:
            gha('error', '%s did not come back intact - the only copy was on this runner. Re-run tfgworkers\' '
                         'deploy-gportal before starting the server.' % f)
            bad += 1
    return 1 if bad else 0


def cmd_marker():
    latest = os.environ['LATEST']
    open('tfg-version.txt', 'w').write(latest)
    if DRY:
        say('WOULD WRITE .tfg-version = %s' % latest)
        return 0
    ok = put_verified('tfg-version.txt', '.tfg-version')
    say('marker on the server wanted %r: %s' % (latest, 'verified' if ok else 'NOT written'))
    if not ok:
        gha('error', 'the version marker did not write; the next run would reinstall again')
        return 1
    summary('## TFG updated to %s' % latest)
    summary('- Players must install the matching client from %s' % os.environ.get('RELEASE_URL', ''))
    summary('- World untouched (wipe_world was not set). Restart the server in G-Portal to load the update.')
    return 0


COMMANDS = {'current': cmd_current, 'release': cmd_release, 'save': cmd_save, 'wipe': cmd_wipe,
            'upload': cmd_upload, 'fixes': cmd_fixes, 'restore': cmd_restore, 'marker': cmd_marker}

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        sys.exit('usage: tfg_ftp.py %s' % '|'.join(COMMANDS))
    if DRY:
        say('*** DRY RUN: read-only. No delete, no put, no rm on the server. ***')
    sys.exit(COMMANDS[sys.argv[1]]())
