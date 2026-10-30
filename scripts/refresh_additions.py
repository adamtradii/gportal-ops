#!/usr/bin/env python3
"""Keep the Crownfall mod lock (pack/crownfall/additions.json) up to date. Stdlib only; tested by test_refresh_additions.py.

For every mod in the lock:
  * source "modrinth" WITHOUT CurseForge ids: ask Modrinth (GET /v2/project/<modrinth_project>/version with
    loaders=["forge"] and game_versions=["1.20.1"]) for the newest RELEASE file, download it, verify size + sha1,
    then re-read its mods.toml (a Forge jar, loaderVersion covers Forge 47, forge/minecraft dependency ranges cover
    47.4.13 / 1.20.1). The newest candidate that passes is adopted; one that fails is skipped (reason printed) and the
    next older one tried, down to the pinned file. filename/url/sha1/size/modrinth_version_id are rewritten.
  * a mod WITH CurseForge ids stays pinned: the client installs it by those ids, so the server jar and the ids must
    move together, and the CurseForge files API needs a key that a runner does not have. A newer file is taken only
    when it is GIVEN in pack/crownfall/cf-updates.json (env CF_UPDATES):
        {"<mod_id>": {"cf_file_id": 123, "filename": "x.jar", "url": "https://...", "sha1": "...", "size": 1234}}
    (url/sha1/size are verified exactly like a Modrinth file). Mods left pinned are listed as such.
  * additions_version is bumped (integer +1) only when at least one mod changed; nothing else in the file is touched.

Prints exactly which mods changed, writes refresh-report.md, GITHUB_OUTPUT (changed=true|false, count=N) and the step
summary. A mod whose lookup fails (API down) keeps its pinned file with a warning: a refresh problem never blocks an
install. Environment: ADDITIONS (default pack/crownfall/additions.json), CF_UPDATES, MODRINTH_API (default
https://api.modrinth.com), ALLOW_PRERELEASE=true (also beta/alpha), SLEEP, DRY_RUN=true (report only, file untouched).
"""
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pack as bp  # noqa: E402
import tfg_ftp  # noqa: E402

API = os.environ.get('MODRINTH_API', 'https://api.modrinth.com').rstrip('/')
FORGE, MC = '47.4.13', '1.20.1'


def say(m=''):
    print(m, flush=True)


def api_versions(slug, tries=4):
    """Modrinth versions of slug for Forge + 1.20.1, newest first. Raises RuntimeError when the API cannot say."""
    q = urllib.parse.urlencode({'loaders': json.dumps(['forge']), 'game_versions': json.dumps([MC])})
    url = '%s/v2/project/%s/version?%s' % (API, urllib.parse.quote(slug, safe=''), q)
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': bp.UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            if not isinstance(data, list):
                raise ValueError('unexpected answer %r' % str(data)[:80])
            vs = [v for v in data if 'forge' in v.get('loaders', []) and MC in v.get('game_versions', [])]
            return sorted(vs, key=lambda v: v.get('date_published', ''), reverse=True)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise RuntimeError('Modrinth project "%s" not found (404)' % slug)
            last = e
        except (OSError, ValueError, urllib.error.URLError) as e:
            last = e
        if i < tries - 1:
            time.sleep(float(os.environ.get('SLEEP', '5')) * (i + 1))
    raise RuntimeError('Modrinth lookup for "%s" failed: %s' % (slug, last))


def primary_file(v):
    files = v.get('files') or []
    for f in files:
        if f.get('primary'):
            return f
    return files[0] if files else None


def vet(cand, cache):
    """Download + verify a candidate dict {filename,url,sha1,size}; returns (path, [reasons])."""
    dest = os.path.join(cache, cand['filename'])
    try:
        bp.download(cand['url'], dest, cand.get('size'), cand['sha1'])
    except bp.BuildError as e:
        return None, ['download refused: %s' % e]
    return dest, bp.check_forge_compat(dest, FORGE, MC)


def refresh_modrinth(mod, cache, allow_pre):
    """Returns ('unchanged'|'changed'|'kept', info). info for changed = new fields dict + 'version_number'."""
    versions = api_versions(mod['modrinth_project'])
    ok_types = {'release'} | ({'beta', 'alpha'} if allow_pre else set())
    skipped = []
    for v in versions:
        f = primary_file(v)
        if not f:
            continue
        sha = (f.get('hashes') or {}).get('sha1', '').lower()
        if v.get('id') == mod.get('modrinth_version_id') or sha == mod.get('sha1'):
            return ('kept' if skipped else 'unchanged'), {'skipped': skipped}
        if v.get('version_type', 'release') not in ok_types:
            skipped.append('%s (%s): not a release' % (v.get('version_number'), v.get('version_type')))
            continue
        cand = {'filename': f['filename'], 'url': f['url'], 'sha1': sha, 'size': f.get('size')}
        if not re.fullmatch(r'[0-9a-f]{40}', sha):
            skipped.append('%s: Modrinth gave no sha1' % v.get('version_number'))
            continue
        path, why = vet(cand, cache)
        if why:
            skipped.append('%s (%s): %s' % (v.get('version_number'), f['filename'], '; '.join(why)))
            continue
        cand['modrinth_version_id'] = v.get('id')
        cand['version_number'] = v.get('version_number')
        cand['skipped'] = skipped
        return 'changed', cand
    return ('kept' if skipped else 'unchanged'), {'skipped': skipped}


def refresh_given(mod, given, cache):
    cand = {k: given.get(k) for k in ('cf_file_id', 'filename', 'url', 'sha1', 'size')}
    if not all(cand[k] for k in ('cf_file_id', 'filename', 'url', 'sha1')):
        return 'kept', {'skipped': ['cf-updates entry needs cf_file_id, filename, url, sha1']}
    cand['sha1'] = cand['sha1'].lower()
    if cand['cf_file_id'] == mod.get('cf_file_id') and cand['sha1'] == mod.get('sha1'):
        return 'unchanged', {'skipped': []}
    path, why = vet(cand, cache)
    if why:
        return 'kept', {'skipped': ['cf-updates %s: %s' % (cand['filename'], '; '.join(why))]}
    cand['version_number'] = cand['filename']
    cand['skipped'] = []
    return 'changed', cand


def bump(ver):
    ver = str(ver)
    if re.fullmatch(r'\d+', ver):
        return str(int(ver) + 1)
    return re.sub(r'(\d+)$', lambda m: str(int(m.group(1)) + 1), ver) if re.search(r'\d$', ver) else ver + '.1'


def run(path, cache='dl-refresh', cf_updates=None, allow_pre=False, write=True):
    with open(path, encoding='utf-8') as f:
        raw = json.load(f)
    add = bp.load_additions(path)                     # validates first: never refresh a broken lock
    cf_updates = cf_updates or {}
    shutil.rmtree(cache, ignore_errors=True)
    os.makedirs(cache, exist_ok=True)
    changes, pinned, warns, unchanged = [], [], [], 0
    for mod, rmod in zip(add['mods'], raw['mods']):
        name = mod['name']
        try:
            if mod['_has_cf']:
                given = cf_updates.get(mod.get('mod_id')) or cf_updates.get(name)
                if not given:
                    pinned.append('%s: CurseForge file %s stays pinned (no key to ask CurseForge; put a newer file in '
                                  'cf-updates.json to move it)' % (name, mod['cf_file_id']))
                    continue
                state, info = refresh_given(mod, given, cache)
            elif mod.get('source') == 'modrinth' and mod.get('modrinth_project'):
                state, info = refresh_modrinth(mod, cache, allow_pre)
            else:
                pinned.append('%s: source %r has no Modrinth project, stays pinned' % (name, mod.get('source')))
                continue
        except RuntimeError as e:
            warns.append('%s: %s - pinned file kept' % (name, e))
            continue
        for s in info.get('skipped', []):
            warns.append('%s: skipped newer file %s' % (name, s))
        if state == 'changed':
            changes.append({'name': name, 'old': mod['filename'], 'new': info['filename'],
                            'version': info.get('version_number'), 'side': mod['side']})
            for k in ('filename', 'url', 'sha1', 'size', 'modrinth_version_id', 'cf_file_id'):
                if info.get(k) is not None:
                    rmod[k] = info[k]
        else:
            unchanged += 1
    old_ver = str(raw.get('additions_version'))
    if changes:
        raw['additions_version'] = bump(old_ver)
        if write:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(raw, f, indent=2, ensure_ascii=False)
                f.write('\n')
    return {'changes': changes, 'pinned': pinned, 'warnings': warns, 'unchanged': unchanged,
            'old_version': old_ver, 'new_version': raw['additions_version']}


def report(r):
    L = []
    if r['changes']:
        L.append('additions_version %s -> %s. CHANGED mods:' % (r['old_version'], r['new_version']))
        for c in r['changes']:
            L.append('  CHANGED %s [%s]: %s -> %s%s' % (c['name'], c['side'], c['old'], c['new'],
                                                       ' (%s)' % c['version'] if c['version'] else ''))
    else:
        L.append('no mod changed; additions_version stays %s' % r['old_version'])
    L.append('%d mod(s) already newest' % r['unchanged'])
    L += ['  PINNED ' + p for p in r['pinned']]
    L += ['  WARNING ' + w for w in r['warnings']]
    return '\n'.join(L)


def main():
    path = os.environ.get('ADDITIONS') or bp.DEFAULT_ADDITIONS
    cfp = os.environ.get('CF_UPDATES') or os.path.join(os.path.dirname(path), 'cf-updates.json')
    cf = json.load(open(cfp)) if os.path.exists(cfp) else {}
    dry = os.environ.get('DRY_RUN', '').lower() == 'true'
    r = run(path, cf_updates=cf, allow_pre=os.environ.get('ALLOW_PRERELEASE', '').lower() == 'true', write=not dry)
    text = report(r)
    say(text)
    open('refresh-report.md', 'w').write(text + '\n')
    out = os.environ.get('GITHUB_OUTPUT')
    if out:
        with open(out, 'a') as f:
            f.write('changed=%s\ncount=%d\n' % ('true' if r['changes'] else 'false', len(r['changes'])))
    tfg_ftp.summary('### Mod refresh\n```\n%s\n```\n' % text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
