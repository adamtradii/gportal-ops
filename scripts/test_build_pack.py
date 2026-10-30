#!/usr/bin/env python3
"""Local tests for scripts/build_pack.py (and the Crownfall bits of scripts/tfg_ftp.py): a fake TFG release (small
zips), a fake additions.json in the agreed format, fake downloads from a local http.server.
Run: python3 scripts/test_build_pack.py"""
import functools
import hashlib
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, 'build_pack.py')
FTP = os.path.join(HERE, 'tfg_ftp.py')
sys.path.insert(0, HERE)
import build_pack  # noqa: E402
import tfg_ftp  # noqa: E402


def make_jar(path, ids, extra=b''):
    toml = ''.join('[[mods]]\nmodId="%s"\nversion="1"\n[[dependencies.%s]]\nmodId="forge"\n' % (i, i) for i in ids)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('META-INF/mods.toml', toml)
        z.writestr('x.class', extra or ids[0].encode())


def sha1(path):
    return hashlib.sha1(open(path, 'rb').read()).hexdigest()


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class World:
    """tmp dir with: srv/ (served over http), run/ (cwd of the tool), the fake TFG release and additions.json."""

    def __init__(self):
        self.w = tempfile.mkdtemp()
        self.srv = os.path.join(self.w, 'srv')
        self.run = os.path.join(self.w, 'run')
        os.makedirs(self.srv)
        os.makedirs(self.run)
        h = functools.partial(Quiet, directory=self.srv)
        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = 'http://127.0.0.1:%d/' % self.httpd.server_address[1]
        self.fake_tfg()
        self.fake_mods()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        shutil.rmtree(self.w, True)

    def fake_tfg(self):
        sp = os.path.join(self.srv, 'serverpack.zip')
        base_jar = os.path.join(self.w, 'basemod.jar')
        make_jar(base_jar, ['basemod'])
        with zipfile.ZipFile(sp, 'w') as z:
            z.write(base_jar, 'mods/basemod-1.0.jar')
            z.writestr('mods/other-1.0.jar', open(base_jar, 'rb').read())
            z.writestr('config/a.toml', 'tfg=1')
            z.writestr('kubejs/server_scripts/x.js', 'x')
            z.writestr('tacz/l.txt', 'l')
            z.writestr('README.md', 'readme')
            z.writestr('start_server.sh', 'skip me')
            z.writestr('server.properties', 'skip me')
            z.writestr('forge-1.20.1-47.4.13-installer.jar', 'skip me')
            z.writestr('libraries/net/x.jar', 'skip me')
        cf = os.path.join(self.srv, 'client.zip')
        with zipfile.ZipFile(cf, 'w') as z:
            z.writestr('manifest.json', json.dumps({
                'minecraft': {'version': '1.20.1', 'modLoaders': [{'id': 'forge-47.4.13', 'primary': True}]},
                'manifestType': 'minecraftModpack', 'manifestVersion': 1, 'name': 'TerraFirmaGreg-Modern',
                'version': '0.13.17', 'author': 'a', 'overrides': 'overrides',
                'files': [{'projectID': 111, 'fileID': 1, 'required': True}]}))
            z.writestr('overrides/', '')
            z.writestr('overrides/mods/steam-1.jar', 'steam')
            z.writestr('overrides/config/a.toml', 'tfg=1')
            z.writestr('overrides/kubejs/client_scripts/c.js', 'c')

    def fake_mods(self):
        self.mods = {}
        for fn, ids in (('serveronly-1.0.jar', ['serveronly']), ('bothcf-1.0.jar', ['bothcf']),
                        ('bothmr-1.0.jar', ['bothmr']), ('clientjar-1.0.jar', ['clientjar'])):
            make_jar(os.path.join(self.srv, fn), ids)
        self.additions = {
            'pack_name': 'TFG Crownfall', 'additions_version': '1',
            'base': {'repo': 'TerraFirmaGreg-Team/Modpack-Modern', 'tracks': 'latest release'},
            'mods': [self.mod('Server Only', 'serveronly', 'server', 'serveronly-1.0.jar', None),
                     self.mod('Both CF', 'bothcf', 'both', 'bothcf-1.0.jar', (222, 2)),
                     self.mod('Both MR', 'bothmr', 'both', 'bothmr-1.0.jar', None),
                     {'name': 'Client CF', 'mod_id': 'clientcf', 'side': 'client', 'source': 'curseforge',
                      'cf_project_id': 333, 'cf_file_id': 3, 'filename': 'clientcf-1.0.jar', 'url': None,
                      'sha1': None, 'size': None, 'requires': [], 'why': 'minimap'},
                     self.mod('Client Jar', 'clientjar', 'client', 'clientjar-1.0.jar', None)],
            'skipped': [], 'already_in_tfg': []}

    def mod(self, name, mid, side, fn, cf):
        p = os.path.join(self.srv, fn)
        return {'name': name, 'mod_id': mid, 'side': side, 'source': 'curseforge' if cf else 'modrinth',
                'cf_project_id': cf[0] if cf else None, 'cf_file_id': cf[1] if cf else None,
                'modrinth_project': mid, 'modrinth_version_id': 'v', 'filename': fn, 'url': self.base + fn,
                'sha1': sha1(p), 'size': os.path.getsize(p), 'requires': [], 'why': 'because'}

    def write_additions(self):
        os.makedirs(os.path.join(self.run, 'pack/crownfall'), exist_ok=True)
        with open(os.path.join(self.run, 'pack/crownfall/additions.json'), 'w') as f:
            json.dump(self.additions, f)

    def overrides(self, files):
        for rel, data in files.items():
            p = os.path.join(self.run, 'pack/crownfall/overrides', rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'w').write(data)

    def release_files(self, tag='0.13.17'):
        for name, val in (('tfg_tag.txt', tag), ('asset_url.txt', self.base + 'serverpack.zip'),
                          ('client_asset_url.txt', self.base + 'client.zip')):
            open(os.path.join(self.run, name), 'w').write(val)

    def tool(self, cmd, **env):
        e = dict(os.environ, SLEEP='0')
        e.setdefault('MIN_STAGED_FILES', '3')
        e.update(env)
        for k in ('PACK', 'DRY_RUN', 'ADDITIONS', 'OVERRIDES', 'GITHUB_REPOSITORY', 'GITHUB_STEP_SUMMARY'):
            if k not in env:
                e.pop(k, None)
        p = subprocess.run([sys.executable, TOOL, cmd], cwd=self.run, env=e, capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def read(self, rel):
        p = os.path.join(self.run, rel)
        return open(p).read() if os.path.exists(p) else None


class T(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.addCleanup(self.w.close)
        self.w.write_additions()
        self.w.release_files()

    # ---- marker / pack version
    def test_pack_version_string_follows_tfg_and_additions(self):
        rc, out = self.w.tool('version')
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.w.read('latest.txt'), '0.13.17+cf1')
        self.assertEqual(self.w.read('release_tag.txt'), 'crownfall-0.13.17+cf1')
        self.w.release_files('v0.13.18')                      # TFG moves -> string moves
        self.w.tool('version')
        self.assertEqual(self.w.read('latest.txt'), '0.13.18+cf1')
        self.w.additions['additions_version'] = '2'            # additions move -> string moves
        self.w.write_additions()
        self.w.tool('version')
        self.assertEqual(self.w.read('latest.txt'), '0.13.18+cf2')

    def test_pack_tfg_fallback_marker_is_the_plain_tag_and_ignores_additions(self):
        os.remove(os.path.join(self.w.run, 'pack/crownfall/additions.json'))
        rc, out = self.w.tool('version', PACK='tfg')
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.w.read('latest.txt'), '0.13.17')
        rc, out = self.w.tool('server', PACK='tfg')
        self.assertEqual(rc, 0, out)
        self.assertEqual(sorted(os.listdir(os.path.join(self.w.run, 'stage/mods'))), ['basemod-1.0.jar', 'other-1.0.jar'])
        self.assertEqual(self.w.read('wipe-extra.txt'), '')

    def test_missing_additions_for_crownfall_fails_with_next_step(self):
        os.remove(os.path.join(self.w.run, 'pack/crownfall/additions.json'))
        rc, out = self.w.tool('version')
        self.assertEqual(rc, 1)
        self.assertIn('NEXT STEP', out)
        self.assertIn('pack=tfg', out)

    def test_release_url_points_at_this_repo_for_crownfall(self):
        self.w.tool('version', GITHUB_REPOSITORY='adamtradii/gportal-ops')
        self.assertEqual(self.w.read('release_url.txt'),
                         'https://github.com/adamtradii/gportal-ops/releases/tag/crownfall-0.13.17%2Bcf1')

    # ---- server tree
    def test_server_tree_has_tfg_plus_server_mods_and_never_client_only(self):
        self.w.overrides({'config/new-mod.toml': 'n=1', 'config/a.toml': 'tfg=2', 'kubejs/server_scripts/y.js': 'y'})
        rc, out = self.w.tool('server')
        self.assertEqual(rc, 0, out)
        mods = sorted(os.listdir(os.path.join(self.w.run, 'stage/mods')))
        self.assertEqual(mods, ['basemod-1.0.jar', 'bothcf-1.0.jar', 'bothmr-1.0.jar', 'other-1.0.jar', 'serveronly-1.0.jar'])
        for client_only in ('clientcf-1.0.jar', 'clientjar-1.0.jar'):
            self.assertNotIn(client_only, mods)
        st = lambda r: self.w.read('stage/' + r)                      # noqa: E731
        self.assertEqual(st('config/a.toml'), 'tfg=2')               # overrides win over TFG's file
        self.assertEqual(st('config/new-mod.toml'), 'n=1')
        self.assertEqual(st('kubejs/server_scripts/x.js'), 'x')
        for skipped in ('start_server.sh', 'server.properties', 'forge-1.20.1-47.4.13-installer.jar', 'libraries'):
            self.assertFalse(os.path.exists(os.path.join(self.w.run, 'stage', skipped)), skipped)
        self.assertEqual(open(os.path.join(self.w.run, 'stage/mods/serveronly-1.0.jar'), 'rb').read(),
                         open(os.path.join(self.w.srv, 'serveronly-1.0.jar'), 'rb').read())
        self.assertIn('replaced', out)

    def test_sha1_mismatch_is_refused_and_nothing_is_staged(self):
        self.w.additions['mods'][1]['sha1'] = '0' * 40
        self.w.write_additions()
        rc, out = self.w.tool('server')
        self.assertEqual(rc, 1, out)
        self.assertIn('bothcf-1.0.jar', out)
        self.assertIn('REFUSED', out)
        self.assertIn('sha1', out)
        self.assertFalse(os.path.exists(os.path.join(self.w.run, 'stage')))

    def test_size_mismatch_is_refused(self):
        self.w.additions['mods'][0]['size'] += 1
        self.w.write_additions()
        rc, out = self.w.tool('server')
        self.assertEqual(rc, 1, out)
        self.assertIn('size', out)
        self.assertFalse(os.path.exists(os.path.join(self.w.run, 'stage')))

    def test_every_problem_is_reported_at_once(self):
        self.w.additions['mods'][0]['sha1'] = 'f' * 40
        self.w.additions['mods'][2]['url'] = self.w.base + 'does-not-exist.jar'
        self.w.write_additions()
        rc, out = self.w.tool('server')
        self.assertEqual(rc, 1, out)
        self.assertIn('serveronly-1.0.jar', out)
        self.assertIn('bothmr-1.0.jar', out)

    def test_validation_lists_all_errors(self):
        a = self.w.additions
        a['mods'][0]['side'] = 'everywhere'
        a['mods'][1]['filename'] = '../evil.jar'
        a['mods'][2]['sha1'] = 'abc'
        a['mods'][4]['url'] = ''
        self.w.write_additions()
        rc, out = self.w.tool('version')
        self.assertEqual(rc, 1)
        for needle in ('side must be', 'plain *.jar', 'sha1 must be', 'no download url'):
            self.assertIn(needle, out)

    def test_duplicate_of_a_tfg_mod_id_is_refused(self):
        make_jar(os.path.join(self.w.srv, 'serveronly-1.0.jar'), ['basemod'])       # same mod id as TFG's jar
        self.w.additions['mods'][0] = self.w.mod('Server Only', 'serveronly', 'server', 'serveronly-1.0.jar', None)
        self.w.write_additions()
        rc, out = self.w.tool('server')
        self.assertEqual(rc, 1, out)
        self.assertIn('mod id "basemod"', out)
        self.assertFalse(os.path.exists(os.path.join(self.w.run, 'stage')))

    def test_dependency_modid_forge_is_not_a_mod_id(self):
        make_jar(os.path.join(self.w.w, 'x.jar'), ['m1', 'm2'])
        self.assertEqual(build_pack.jar_mod_ids(os.path.join(self.w.w, 'x.jar')), {'m1', 'm2'})

    def test_tiny_base_payload_is_refused(self):
        rc, out = self.w.tool('server', MIN_STAGED_FILES='1000')
        self.assertEqual(rc, 1, out)
        self.assertIn('refusing to wipe', out)

    def test_extra_override_folders_become_wipe_folders_but_protected_ones_fail(self):
        self.w.overrides({'resourcepacks/p.txt': 'p', 'config/a.toml': 'c'})
        rc, out = self.w.tool('server')
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.w.read('wipe-extra.txt'), 'resourcepacks\n')
        self.w.overrides({'minecolonies/colonies.dat': 'would be wiped'})
        rc, out = self.w.tool('server')
        self.assertEqual(rc, 1, out)
        self.assertIn('minecolonies', out)

    # ---- client zip
    def test_client_manifest_is_extended_and_modrinth_only_mods_become_override_jars(self):
        self.w.overrides({'config/new-mod.toml': 'n=1', 'config/a.toml': 'tfg=2'})
        rc, out = self.w.tool('client')
        self.assertEqual(rc, 0, out)
        zp = self.w.read('client_zip.txt')
        self.assertEqual(os.path.basename(zp), 'TFG-Crownfall-0.13.17-cf1-client.zip')
        z = zipfile.ZipFile(os.path.join(self.w.run, zp))
        m = json.loads(z.read('manifest.json'))
        self.assertEqual((m['name'], m['version']), ('TFG Crownfall', '0.13.17+cf1'))
        self.assertEqual(m['minecraft']['modLoaders'][0]['id'], 'forge-47.4.13')
        self.assertEqual(m['files'], [{'projectID': 111, 'fileID': 1, 'required': True},
                                      {'projectID': 222, 'fileID': 2, 'required': True},
                                      {'projectID': 333, 'fileID': 3, 'required': True}])
        names = set(z.namelist())
        self.assertIn('overrides/mods/steam-1.jar', names)              # TFG's own entries survive
        self.assertIn('overrides/mods/serveronly-1.0.jar'.replace('serveronly', 'bothmr'), names)
        self.assertIn('overrides/mods/clientjar-1.0.jar', names)
        self.assertNotIn('overrides/mods/serveronly-1.0.jar', names)    # server-only never goes to the client
        self.assertNotIn('overrides/mods/bothcf-1.0.jar', names)        # has CurseForge ids -> manifest, not a jar
        self.assertEqual(z.read('overrides/config/a.toml'), b'tfg=2')   # override replaced TFG's file ...
        self.assertEqual(sum(1 for n in z.namelist() if n == 'overrides/config/a.toml'), 1)   # ... exactly once
        self.assertEqual(z.read('overrides/config/new-mod.toml'), b'n=1')
        self.assertIn('overrides/kubejs/client_scripts/c.js', names)
        self.assertIn('Client Jar', open(os.path.join(self.w.run, 'dist/RELEASE_NOTES.md')).read())

    def test_client_refuses_a_curseforge_project_tfg_already_has(self):
        self.w.additions['mods'][1]['cf_project_id'] = 111
        self.w.write_additions()
        rc, out = self.w.tool('client')
        self.assertEqual(rc, 1, out)
        self.assertIn('already in TFG', out)

    def test_client_bad_sha_on_a_jar_is_refused(self):
        self.w.additions['mods'][4]['sha1'] = '1' * 40
        self.w.write_additions()
        rc, out = self.w.tool('client')
        self.assertEqual(rc, 1, out)
        self.assertIn('REFUSED', out)

    def test_client_command_is_crownfall_only(self):
        rc, out = self.w.tool('client', PACK='tfg')
        self.assertNotEqual(rc, 0)

    # ---- dry run chain: build, then the FTP script's dry run shows the added mods and changes nothing
    def test_dry_run_plan_lists_added_mods_and_changes_nothing_on_the_server(self):
        self.w.overrides({'resourcepacks/p.txt': 'p'})
        self.assertEqual(self.w.tool('version')[0], 0)
        rc, out = self.w.tool('server', DRY_RUN='true')
        self.assertEqual(rc, 0, out)
        self.assertIn('DRY RUN', out)
        server = os.path.join(self.w.w, 'ftp')
        os.makedirs(os.path.join(server, 'mods'))
        open(os.path.join(server, 'mods/old.jar'), 'w').write('old')
        os.makedirs(os.path.join(server, 'world/minecolonies'))
        open(os.path.join(server, 'world/minecolonies/colonies.dat'), 'w').write('COLONIES')
        env = dict(os.environ, SLEEP='0', HOST='h', FPASS='pw', FUSER='u', DRY_RUN='true',
                   LFTP_CMD=json.dumps([sys.executable, os.path.join(HERE, 'fake_lftp.py'), 'file://' + server]),
                   FAKE_STATE=os.path.join(self.w.w, 'state.json'))
        for cmd in ('wipe', 'upload'):
            p = subprocess.run([sys.executable, FTP, cmd], cwd=self.w.run, env=env, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            if cmd == 'wipe':
                self.assertIn('resourcepacks', p.stdout)                 # the extra folder is in the plan
        plan = open(os.path.join(self.w.run, 'chunks/0000.lftp')).read() + ''.join(
            open(os.path.join(self.w.run, 'chunks', f)).read() for f in sorted(os.listdir(os.path.join(self.w.run, 'chunks'))))
        self.assertIn('mods/serveronly-1.0.jar', plan)
        self.assertEqual(open(os.path.join(server, 'mods/old.jar')).read(), 'old')
        self.assertEqual(open(os.path.join(server, 'world/minecolonies/colonies.dat')).read(), 'COLONIES')

    def test_real_wipe_keeps_the_world_with_minecolonies_data_and_takes_extra_folders(self):
        self.w.overrides({'resourcepacks/p.txt': 'p'})
        self.w.tool('server')
        server = os.path.join(self.w.w, 'ftp')
        for rel in ('mods/old.jar', 'resourcepacks/old.zip', 'world/minecolonies/colonies.dat', 'world/data/x.dat',
                    'logs/latest.log', 'DiscordIntegration-Data/Messages.toml'):
            os.makedirs(os.path.dirname(os.path.join(server, rel)), exist_ok=True)
            open(os.path.join(server, rel), 'w').write('keep' if rel.startswith(('world', 'logs', 'Discord')) else 'x')
        env = dict(os.environ, SLEEP='0', HOST='h', FPASS='pw', FUSER='u',
                   LFTP_CMD=json.dumps([sys.executable, os.path.join(HERE, 'fake_lftp.py'), 'file://' + server]),
                   FAKE_STATE=os.path.join(self.w.w, 'state.json'))
        env.pop('DRY_RUN', None)
        p = subprocess.run([sys.executable, FTP, 'wipe'], cwd=self.w.run, env=env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertFalse(os.path.exists(os.path.join(server, 'mods/old.jar')))
        self.assertFalse(os.path.exists(os.path.join(server, 'resourcepacks/old.zip')))
        for rel in ('world/minecolonies/colonies.dat', 'world/data/x.dat', 'logs/latest.log', 'DiscordIntegration-Data/Messages.toml'):
            self.assertEqual(open(os.path.join(server, rel)).read(), 'keep', rel)

    def test_wipe_refuses_a_protected_folder_in_wipe_extra_before_deleting_anything(self):
        server = os.path.join(self.w.w, 'ftp')
        os.makedirs(os.path.join(server, 'mods'))
        open(os.path.join(server, 'mods/old.jar'), 'w').write('x')
        for bad in ('world', 'world_nether', 'minecolonies', 'logs', '../etc', 'a/b', '.git'):
            open(os.path.join(self.w.run, 'wipe-extra.txt'), 'w').write('resourcepacks\n%s\n' % bad)
            env = dict(os.environ, SLEEP='0', HOST='h', FPASS='pw', FUSER='u',
                       LFTP_CMD=json.dumps([sys.executable, os.path.join(HERE, 'fake_lftp.py'), 'file://' + server]),
                       FAKE_STATE=os.path.join(self.w.w, 'state.json'))
            env.pop('DRY_RUN', None)
            p = subprocess.run([sys.executable, FTP, 'wipe'], cwd=self.w.run, env=env, capture_output=True, text=True)
            self.assertEqual(p.returncode, 1, bad + p.stdout + p.stderr)
            self.assertTrue(os.path.exists(os.path.join(server, 'mods/old.jar')), bad)

    # ---- tfg_ftp release helpers
    def test_pick_client_asset_and_server_asset_names(self):
        r = {'tag_name': '0.13.17', 'assets': [{'name': 'TerraFirmaGreg-Modern-0.13.17-curseforge.zip'},
                                               {'name': 'TerraFirmaGreg-Modern-0.13.17-serverpack.zip'}]}
        self.assertEqual(tfg_ftp.pick_client_asset(r)['name'], 'TerraFirmaGreg-Modern-0.13.17-curseforge.zip')
        self.assertEqual(tfg_ftp.pick_release([dict(r, draft=False, prerelease=False)])[1]['name'],
                         'TerraFirmaGreg-Modern-0.13.17-serverpack.zip')
        self.assertIsNone(tfg_ftp.pick_client_asset({'assets': []}))


if __name__ == '__main__':
    unittest.main(verbosity=1)
