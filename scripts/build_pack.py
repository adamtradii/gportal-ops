#!/usr/bin/env python3
"""Builds the "TFG Crownfall" pack: TerraFirmaGreg (TFG) Modern + the Crownfall mods (pack/crownfall/additions.json).

Used by .github/workflows/tfg-update.yml (server tree) and .github/workflows/pack-release.yml (client zip).
Stdlib only. Tested by scripts/test_build_pack.py.

Subcommands (cwd = the workflow's work dir; all state in plain files, like scripts/tfg_ftp.py):
  version   after `tfg_ftp.py release` (needs tfg_tag.txt): writes latest.txt = the PACK VERSION that the
            `.tfg-version` marker on the server will hold, pack_version.txt, release_tag.txt, release_url.txt.
  server    downloads TFG's serverpack (asset_url.txt), downloads + verifies every additions mod for the server,
            stages everything into stage/ (what tfg_ftp.py uploads) and writes wipe-extra.txt.
  client    downloads TFG's CurseForge zip (client_asset_url.txt), extends its manifest.json and builds
            dist/<TFG-Crownfall-...-client.zip> for the CurseForge app's Import, plus dist/RELEASE_NOTES.md.

Everything that can fail (a bad hash, a missing url, a duplicate mod) fails HERE, before the workflow's first
destructive FTP step, and every problem is printed at once with the next step.

Environment: PACK=crownfall|tfg (default crownfall; tfg = plain TFG, additions ignored), ADDITIONS (default
pack/crownfall/additions.json), OVERRIDES (default pack/crownfall/overrides), MIN_STAGED_FILES (default 1000),
SLEEP (seconds between download retries, default 5), GITHUB_REPOSITORY (release url), DRY_RUN (only printed).

Pack version = "<tfg tag>+cf<additions_version>" (e.g. 0.13.17+cf1); for PACK=tfg it is the plain TFG tag. A change of
EITHER part changes the string, and the updater installs whenever the marker differs.
"""
import hashlib
import http.client
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tfg_ftp  # noqa: E402  (WIPE_DIRS, protected-dir rule, summary/say helpers)

UA = 'tfg-crownfall-pack'
SIDES = ('both', 'server', 'client')
DEFAULT_ADDITIONS = 'pack/crownfall/additions.json'
DEFAULT_OVERRIDES = 'pack/crownfall/overrides'
SKIP_BASE_DIRS = {'libraries'}                    # G-Portal owns the Forge runtime
NET_ERRORS = (urllib.error.URLError, OSError, http.client.HTTPException, TimeoutError)


class BuildError(Exception):
    pass


def say(msg=''):
    print(msg, flush=True)


def fail(errors, hint=None):
    for e in errors:
        tfg_ftp.gha('error', e)
    if hint:
        say('NEXT STEP: ' + hint)
    raise SystemExit(1)


def sleep():
    s = float(os.environ.get('SLEEP', '5'))
    if s:
        time.sleep(s)


# ---------------------------------------------------------------- additions.json
def load_additions(path):
    """Read + validate additions.json. Returns the dict (mods normalised). Raises SystemExit listing EVERY problem."""
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        fail(['%s does not exist' % path],
             'merge branch feat/crownfall-lock (it writes pack/crownfall/additions.json), or run the update with '
             'pack=tfg for plain TFG.')
    except ValueError as e:
        fail(['%s is not valid JSON: %s' % (path, e)])
    errs = []
    if not isinstance(data, dict):
        fail(['%s must be a JSON object' % path])
    ver = str(data.get('additions_version', '')).strip()
    if not re.fullmatch(r'[0-9A-Za-z][0-9A-Za-z.\-]*', ver):
        errs.append('additions_version %r must be letters/digits/dots/dashes (it becomes part of the pack version)' % ver)
    data['additions_version'] = ver
    data['pack_name'] = str(data.get('pack_name') or 'TFG Crownfall').strip()
    mods = data.get('mods')
    if not isinstance(mods, list):
        errs.append('"mods" must be a list')
        mods = []
    seen = {}
    for i, m in enumerate(mods):
        label = '%s (#%d)' % (m.get('name', '?') if isinstance(m, dict) else '?', i)
        if not isinstance(m, dict):
            errs.append('mod %s is not an object' % label)
            continue
        if m.get('side') not in SIDES:
            errs.append('%s: side must be one of %s, got %r' % (label, '|'.join(SIDES), m.get('side')))
            continue
        fn = m.get('filename')
        if not (isinstance(fn, str) and fn.endswith('.jar') and '/' not in fn and '\\' not in fn
                and fn not in ('.jar', '..') and not fn.startswith('.')):
            errs.append('%s: filename %r must be a plain *.jar name' % (label, fn))
            continue
        if fn in seen:
            errs.append('%s: filename %s is listed twice (also %s)' % (label, fn, seen[fn]))
        seen[fn] = label
        cf = (m.get('cf_project_id'), m.get('cf_file_id'))
        has_cf = all(isinstance(x, int) and not isinstance(x, bool) and x > 0 for x in cf)
        if any(x is not None for x in cf) and not has_cf:
            errs.append('%s: cf_project_id and cf_file_id must both be positive integers or both null' % label)
        m['_has_cf'] = has_cf
        m['_client'] = m['side'] in ('both', 'client')
        m['_server'] = m['side'] in ('both', 'server')
        # a jar is downloaded when the server needs it, or the client needs it and CurseForge cannot supply it
        m['_download'] = m['_server'] or (m['_client'] and not has_cf)
        if m['_download']:
            if not (isinstance(m.get('url'), str) and m['url'].strip()):
                errs.append('%s: no download url (side=%s, curseforge ids %s). Third-party downloads may be disabled '
                            'for this CurseForge file: take the jar from Modrinth or drop the mod'
                            % (label, m['side'], 'present' if has_cf else 'missing'))
            if not re.fullmatch(r'[0-9a-fA-F]{40}', str(m.get('sha1') or '')):
                errs.append('%s: sha1 must be 40 hex characters (a jar is never installed unchecked)' % label)
            else:
                m['sha1'] = m['sha1'].lower()
            if m.get('size') is not None and not (isinstance(m['size'], int) and m['size'] > 0):
                errs.append('%s: size must be a positive integer or null' % label)
        if m['_client'] and not has_cf and not m['_download']:
            errs.append('%s: client mod with no CurseForge ids and no url' % label)
    if errs:
        fail(['%s: %s' % (path, e) for e in errs], 'fix additions.json (branch feat/crownfall-lock owns it).')
    return data


def pack_version(tfg_tag, additions, pack='crownfall'):
    tag = tfg_tag.strip().lstrip('v')
    if pack == 'tfg':
        return tag
    return '%s+cf%s' % (tag, additions['additions_version'])


def slug(pack_name):
    return re.sub(r'[^0-9A-Za-z]+', '-', pack_name).strip('-') or 'pack'


def zip_name(additions, ver):
    """No '+' in file names: GitHub rewrites some characters in release asset names."""
    return '%s-%s-client.zip' % (slug(additions['pack_name']), ver.replace('+cf', '-cf'))


def release_tag(ver):
    return 'crownfall-' + ver


# ---------------------------------------------------------------- downloads
def download(url, dest, size=None, sha1=None, tries=3, timeout=300):
    """Download url to dest. A size/sha1 mismatch is refused at once (no retry: the content is what it is); network
    errors are retried. Raises BuildError."""
    last = None
    os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
    for i in range(tries):
        part = dest + '.part'
        try:
            h, n = hashlib.sha1(), 0
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/octet-stream'})
            with urllib.request.urlopen(req, timeout=timeout) as r, open(part, 'wb') as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    h.update(chunk)
                    n += len(chunk)
        except NET_ERRORS as e:
            last = 'download failed (%s)' % e
            say('  try %d/%d: %s' % (i + 1, tries, last))
            if i < tries - 1:
                sleep()
            continue
        if size is not None and n != size:
            os.remove(part)
            raise BuildError('size %d bytes, expected %d' % (n, size))
        if sha1 and h.hexdigest() != sha1:
            os.remove(part)
            raise BuildError('sha1 %s, expected %s' % (h.hexdigest(), sha1))
        os.replace(part, dest)
        return
    raise BuildError(last or 'download failed')


def fetch_mods(mods, cache):
    """Download every mod flagged _download into cache/<filename>; returns {filename: path}. Fails with ALL problems."""
    paths, errs = {}, []
    for m in mods:
        if not m['_download']:
            continue
        dest = os.path.join(cache, m['filename'])
        say('mod %-40s %s' % (m['filename'], m['side']))
        try:
            download(m['url'], dest, m.get('size'), m['sha1'])
            paths[m['filename']] = dest
        except BuildError as e:
            errs.append('%s (%s): %s - REFUSED' % (m.get('name', m['filename']), m['filename'], e))
    if errs:
        fail(errs, 'nothing on the server was touched. If a hash changed upstream, regenerate additions.json '
                   '(branch feat/crownfall-lock); if only a download failed, re-run.')
    return paths


# ---------------------------------------------------------------- jars
def jar_mod_ids(path):
    """modId of every [[mods]] entry in META-INF/mods.toml (dependency sections are ignored). None = unreadable."""
    try:
        with zipfile.ZipFile(path) as z:
            try:
                text = z.read('META-INF/mods.toml').decode('utf-8', 'replace')
            except KeyError:
                return set()
    except (zipfile.BadZipFile, OSError):
        return None
    ids, section = set(), ''
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('['):
            section = s.strip('[] \t')
        elif section == 'mods':
            m = re.match(r'modId\s*=\s*["\']([^"\']+)["\']', s)
            if m:
                ids.add(m.group(1))
    return ids


def check_duplicates(base_jars, add_jars):
    """The classic boot crash is two jars for one mod. base_jars/add_jars: {filename: path}. Returns error strings."""
    errs, owner = [], {}
    for fn, p in base_jars.items():
        for i in (jar_mod_ids(p) or ()):
            owner.setdefault(i, fn)
    for fn, p in sorted(add_jars.items()):
        if fn in base_jars:
            errs.append('%s: TFG already ships a jar with this exact file name' % fn)
        ids = jar_mod_ids(p)
        if ids is None:
            errs.append('%s: not a readable jar (zip)' % fn)
            continue
        for i in sorted(ids):
            if i in owner:
                errs.append('%s: mod id "%s" is already provided by %s (two jars of one mod crash the boot)'
                            % (fn, i, owner[i]))
            owner[i] = fn
    return errs


# ---------------------------------------------------------------- server tree
def skip_base(fn):
    l = fn.lower()
    return (l.endswith(('.bat', '.sh', '.ps1')) or 'installer' in l or re.match(r'(?:neo)?forge-[\d.]', l)
            or l.startswith('minecraft_server') or l in ('user_jvm_args.txt', 'server.properties'))


def stage_base(zip_path, stage, workdir):
    """TFG serverpack zip -> stage/ with the updater's long-standing skip rules. Returns file count."""
    with zipfile.ZipFile(zip_path) as z:
        bad = z.testzip()
        if bad:
            raise BuildError('corrupt download, first bad member: %s' % bad)
        un = os.path.join(workdir, 'unpack')
        shutil.rmtree(un, ignore_errors=True)
        z.extractall(un)
    root = un
    kids = os.listdir(root)
    if len(kids) == 1 and os.path.isdir(os.path.join(root, kids[0])):
        root = os.path.join(root, kids[0])
    n = 0
    for dp, dns, fns in os.walk(root):
        rel = os.path.relpath(dp, root)
        if rel.split(os.sep)[0] in SKIP_BASE_DIRS:
            dns[:] = []
            continue
        for fn in fns:
            if rel == '.' and skip_base(fn):
                continue
            dst = os.path.join(stage, fn) if rel == '.' else os.path.join(stage, rel, fn)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(dp, fn), dst)
            n += 1
    shutil.rmtree(un, ignore_errors=True)
    return n


def overlay(overrides, dst_root):
    """Copy the overrides tree over dst_root. Returns (files copied, [paths that replaced an existing file])."""
    copied, replaced = 0, []
    if not overrides or not os.path.isdir(overrides):
        return 0, []
    for dp, dns, fns in os.walk(overrides):
        dns.sort()
        for fn in sorted(fns):
            if fn == '.gitkeep':
                continue
            src = os.path.join(dp, fn)
            rel = os.path.relpath(src, overrides)
            dst = os.path.join(dst_root, rel)
            if os.path.exists(dst):
                replaced.append(rel.replace(os.sep, '/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            copied += 1
    return copied, replaced


def extra_wipe_dirs(overrides):
    """Top-level folders the overrides bring that a reinstall must refresh (the default pack folders excluded).
    A protected folder (world, logs, minecolonies, ...) in the overrides is a build error, never a wipe."""
    out, bad = [], []
    if overrides and os.path.isdir(overrides):
        for d in sorted(os.listdir(overrides)):
            if not os.path.isdir(os.path.join(overrides, d)) or d in tfg_ftp.WIPE_DIRS:
                continue
            (out if tfg_ftp.valid_wipe_dir(d) else bad).append(d)
    return out, bad


def build_server(additions, stage='stage', workdir='.', overrides=None, min_files=1000):
    """The whole server tree. Nothing is staged until every download has been verified."""
    mods = additions['mods'] if additions else []
    overrides = overrides if additions else None
    extras, bad = extra_wipe_dirs(overrides)
    if bad:
        fail(['overrides contain the protected folder(s) %s: they hold world/runtime data and are never wiped or '
              'replaced by the updater' % ', '.join(bad)], 'move that content elsewhere or drop it.')
    cache = os.path.join(workdir, 'dl')
    add_paths = fetch_mods([m for m in mods if m['_server']], cache)
    shutil.rmtree(stage, ignore_errors=True)
    try:
        say('downloading the TFG serverpack')
        zp = os.path.join(workdir, 'serverpack.zip')
        download(open(os.path.join(workdir, 'asset_url.txt')).read().strip(), zp)
        n = stage_base(zp, stage, workdir)
    except BuildError as e:
        shutil.rmtree(stage, ignore_errors=True)
        fail(['TFG serverpack: %s' % e], 'nothing on the server was touched; re-run.')
    if n < min_files:
        shutil.rmtree(stage, ignore_errors=True)
        fail(['only %d files staged - refusing to wipe the server for a payload that small' % n])
    say('staged %d TFG files' % n)
    mods_dir = os.path.join(stage, 'mods')
    os.makedirs(mods_dir, exist_ok=True)
    base_jars = {f: os.path.join(mods_dir, f) for f in os.listdir(mods_dir) if f.endswith('.jar')}
    errs = check_duplicates(base_jars, add_paths)
    if errs:
        shutil.rmtree(stage, ignore_errors=True)
        fail(errs, 'remove the listed mod(s) from pack/crownfall/additions.json (TFG already has them), or pin an '
                   'older TFG release with version_match.')
    for fn, p in sorted(add_paths.items()):
        shutil.copyfile(p, os.path.join(mods_dir, fn))
    copied, replaced = overlay(overrides, stage)
    with open(os.path.join(workdir, 'wipe-extra.txt'), 'w') as f:
        f.write(''.join(d + '\n' for d in extras))
    say('added %d mod jar(s) (server side), %d override file(s) (%d replaced a TFG file), extra wipe folders: %s'
        % (len(add_paths), copied, len(replaced), ', '.join(extras) or 'none'))
    if replaced:
        say('overrides replaced: ' + ', '.join(replaced[:40]) + (' ...' if len(replaced) > 40 else ''))
    return {'tfg_files': n, 'mods': sorted(add_paths), 'overrides': copied, 'replaced': replaced, 'extra_wipe': extras}


# ---------------------------------------------------------------- client zip
def build_client(additions, base_zip, out_zip, tfg_tag, overrides, cache):
    """TFG's CurseForge zip + our manifest additions + jars/overrides. Returns (manifest, listing dict)."""
    ver = pack_version(tfg_tag, additions)
    mods = additions['mods']
    cf_mods = [m for m in mods if m['_client'] and m['_has_cf']]
    jar_mods = [m for m in mods if m['_client'] and not m['_has_cf']]
    jars = fetch_mods(jar_mods, cache)
    with zipfile.ZipFile(base_zip) as zin:
        manifest = json.loads(zin.read('manifest.json').decode('utf-8'))
        have = {f.get('projectID') for f in manifest.get('files', [])}
        errs = ['%s: CurseForge project %s is already in TFG\'s own manifest (two files of one project)'
                % (m['name'], m['cf_project_id']) for m in cf_mods if m['cf_project_id'] in have]
        if errs:
            fail(errs, 'remove those mods from additions.json (TFG already has them) or pin an older TFG release.')
        manifest['name'] = additions['pack_name']
        manifest['version'] = ver
        manifest['files'] = list(manifest.get('files', [])) + [
            {'projectID': m['cf_project_id'], 'fileID': m['cf_file_id'], 'required': True} for m in cf_mods]
        prefix = (manifest.get('overrides') or 'overrides').strip('/') + '/'
        # files we add (jars first, then the overrides tree, which wins) -> zip name -> source path
        new = {prefix + 'mods/' + fn: p for fn, p in jars.items()}
        base_names = set(zin.namelist())
        clash = [fn for fn in jars if prefix + 'mods/' + fn in base_names]
        if clash:
            fail(['%s: TFG already ships a jar with this exact file name' % fn for fn in clash])
        ov_names = []
        if overrides and os.path.isdir(overrides):
            for dp, dns, fns in os.walk(overrides):
                for fn in fns:
                    if fn != '.gitkeep':
                        src = os.path.join(dp, fn)
                        name = prefix + os.path.relpath(src, overrides).replace(os.sep, '/')
                        new[name] = src
                        ov_names.append(name)
        os.makedirs(os.path.dirname(out_zip) or '.', exist_ok=True)
        with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
            zout.writestr('manifest.json', json.dumps(manifest, indent=2))
            for info in zin.infolist():
                if info.filename == 'manifest.json' or info.filename in new:
                    continue
                zout.writestr(info, zin.read(info.filename))
            for name, src in sorted(new.items()):
                zout.write(src, name)
    return manifest, {'cf_mods': cf_mods, 'jar_mods': jar_mods, 'overrides': ov_names}


def release_notes(additions, ver, tfg_tag, listing):
    L = ['# %s %s' % (additions['pack_name'], ver), '',
         'TerraFirmaGreg Modern %s + the Crownfall mods (additions version %s).' % (tfg_tag, additions['additions_version']),
         '', '**Install:** CurseForge app -> Create Custom Profile -> Import -> pick this zip. Same Forge as TFG '
         '(1.20.1, forge-47.4.13).', '', '## Added mods', '']
    for m in additions['mods']:
        if m['_client']:
            via = 'CurseForge' if m['_has_cf'] else 'jar in overrides/mods'
            L.append('- %s (%s, %s) - %s' % (m['name'], m['side'], via, m.get('why') or ''))
    L += ['', '(%d override file(s) for config/kubejs.)' % len(listing['overrides']), '']
    return '\n'.join(L)


# ---------------------------------------------------------------- commands
def env_pack():
    p = (os.environ.get('PACK') or 'crownfall').strip().lower()
    if p not in ('crownfall', 'tfg'):
        raise SystemExit('PACK must be crownfall or tfg, got %r' % p)
    return p


def get_additions(pack):
    if pack == 'tfg':
        return None
    return load_additions(os.environ.get('ADDITIONS') or DEFAULT_ADDITIONS)


def cmd_version():
    pack = env_pack()
    tag = open('tfg_tag.txt').read().strip()
    add = get_additions(pack)
    ver = pack_version(tag, add, pack)
    open('latest.txt', 'w').write(ver)
    open('pack_version.txt', 'w').write(ver)
    say('pack: %s, TFG release %s, pack version (the .tfg-version marker): %s' % (pack, tag, ver))
    if add:
        n_srv = sum(1 for m in add['mods'] if m['_server'])
        n_cli = sum(1 for m in add['mods'] if m['_client'])
        say('additions version %s: %d mod(s) (%d server, %d client)' % (add['additions_version'], len(add['mods']), n_srv, n_cli))
        open('release_tag.txt', 'w').write(release_tag(ver))
        repo = os.environ.get('GITHUB_REPOSITORY')
        if repo:    # players of the Crownfall pack get THIS repo's client zip, not TFG's
            open('release_url.txt', 'w').write('https://github.com/%s/releases/tag/%s'
                                              % (repo, urllib.parse.quote(release_tag(ver))))
    return 0


def cmd_server():
    pack = env_pack()
    add = get_additions(pack)
    ov = os.environ.get('OVERRIDES') or DEFAULT_OVERRIDES
    r = build_server(add, overrides=ov, min_files=int(os.environ.get('MIN_STAGED_FILES', '1000')))
    tfg_ftp.summary('### Pack %s (%s)\n- TFG files: %d\n- added mods (server): %s\n- override files: %d (replacing %d TFG files)'
                    '\n- extra folders wiped on reinstall: %s\n' % (
                        pack, open('latest.txt').read() if os.path.exists('latest.txt') else '?', r['tfg_files'],
                        ', '.join(r['mods']) or 'none', r['overrides'], len(r['replaced']), ', '.join(r['extra_wipe']) or 'none'))
    if os.environ.get('DRY_RUN', '').lower() == 'true':
        say('DRY RUN: the tree above is only staged on the runner; the FTP steps print their plans without touching the server')
    return 0


def cmd_client():
    if env_pack() != 'crownfall':
        raise SystemExit('the client zip only exists for PACK=crownfall (plain TFG players use TFG\'s own zip)')
    add = get_additions('crownfall')
    tag = open('tfg_tag.txt').read().strip()
    ver = pack_version(tag, add)
    base = 'client-base.zip'
    say('downloading TFG\'s CurseForge zip')
    try:
        download(open('client_asset_url.txt').read().strip(), base)
    except BuildError as e:
        fail(['TFG curseforge zip: %s' % e], 're-run.')
    out = os.path.join('dist', zip_name(add, ver))
    manifest, listing = build_client(add, base, out, tag, os.environ.get('OVERRIDES') or DEFAULT_OVERRIDES, 'dl')
    open('client_zip.txt', 'w').write(out)
    open(os.path.join('dist', 'RELEASE_NOTES.md'), 'w').write(release_notes(add, ver, tag, listing))
    say('built %s (%d MB): manifest "%s" %s, %d CurseForge file(s) total (+%d added), %d jar(s) in overrides/mods'
        % (out, os.path.getsize(out) >> 20, manifest['name'], manifest['version'], len(manifest['files']),
           len(listing['cf_mods']), len(listing['jar_mods'])))
    return 0


COMMANDS = {'version': cmd_version, 'server': cmd_server, 'client': cmd_client}

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        sys.exit('usage: build_pack.py %s' % '|'.join(COMMANDS))
    sys.exit(COMMANDS[sys.argv[1]]())
