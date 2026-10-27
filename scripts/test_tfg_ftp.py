#!/usr/bin/env python3
"""Local tests for scripts/tfg_ftp.py: real lftp against a throw-away directory (file:// backend), with the
incident's FTP failures injected by scripts/fake_lftp.py.   Run: python3 scripts/test_tfg_ftp.py"""
import json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, 'tfg_ftp.py')
sys.path.insert(0, HERE)
import tfg_ftp  # noqa: E402


class Env:
    def __init__(self):
        self.w = tempfile.mkdtemp()
        self.srv = os.path.join(self.w, 'srv')
        self.cwd = os.path.join(self.w, 'run')
        os.makedirs(self.srv)
        os.makedirs(self.cwd)

    def stage(self, files):
        for rel, data in files.items():
            p = os.path.join(self.cwd, 'stage', rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'w') as f:
                f.write(data)

    def remote(self, files):
        for rel, data in files.items():
            p = os.path.join(self.srv, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'w') as f:
                f.write(data)

    def read(self, rel):
        p = os.path.join(self.srv, rel)
        if not os.path.exists(p):
            return None
        with open(p) as f:
            return f.read()

    def run(self, cmd, **extra):
        env = dict(os.environ, SLEEP='0', HOST='h', FPASS='secretpw', FUSER='u',
                   LFTP_CMD=json.dumps([sys.executable, os.path.join(HERE, 'fake_lftp.py'), 'file://' + self.srv]),
                   FAKE_STATE=os.path.join(self.w, 'state.json'), **extra)
        env.pop('DRY_RUN', None) if 'DRY_RUN' not in extra else None
        p = subprocess.run([sys.executable, TOOL, cmd], cwd=self.cwd, env=env, capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr


def pack():
    d = {'README.md': 'new readme', 'server_starter.conf': 'conf-new-longer-than-old'}
    for i in range(30):
        d['mods/m%02d.jar' % i] = 'jar%d' % i * 5
    d['mods/odd name (1)+x.jar'] = 'spaces'
    d['config/a.toml'] = 'a=1'
    d['config/sub/b.toml'] = 'b=2'
    d['tacz/LICENSE.txt'] = 'lic'
    d['tacz/Create Armorer-v1.2.0.zip'] = 'zip'
    return d


class T(unittest.TestCase):
    def setUp(self):
        self.e = Env()
        self.addCleanup(shutil.rmtree, self.e.w, True)

    def test_incident_stale_equal_smaller_larger_files_are_overwritten(self):
        self.e.stage(pack())
        # server state after a wipe that "left some old files": equal size, smaller, larger, and top-level ones
        self.e.remote({'README.md': 'old readme much much longer than the new one', 'server_starter.conf': 'x',
                       'tacz/LICENSE.txt': 'lic', 'mods/m00.jar': 'jar0' * 5, 'mods/m01.jar': 'j'})
        rc, out = self.e.run('upload', FAKE_EXISTS_ERR='1')
        self.assertEqual(rc, 0, out)
        for rel, data in pack().items():
            self.assertEqual(self.e.read(rel), data, rel)
        self.assertNotIn('put -c', open(os.path.join(self.e.cwd, 'chunks/0000.lftp')).read())

    def test_failed_file_is_retried_and_other_chunk_files_still_upload(self):
        self.e.stage(pack())
        rc, out = self.e.run('upload', FAKE_FAIL=json.dumps({'mods/m05.jar': 1}))
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.e.read('mods/m05.jar'), pack()['mods/m05.jar'])

    def test_permanent_failure_is_reported_by_name_and_job_fails_but_rest_uploaded(self):
        self.e.stage(pack())
        rc, out = self.e.run('upload', FAKE_FAIL=json.dumps({'tacz/LICENSE.txt': 99}))
        self.assertEqual(rc, 1, out)
        self.assertIn('tacz/LICENSE.txt', out)
        self.assertIn('upload-failed.txt', os.listdir(self.e.cwd))
        self.assertEqual(self.e.read('mods/m29.jar'), pack()['mods/m29.jar'])
        self.assertIsNone(self.e.read('tacz/LICENSE.txt'))

    def test_error_in_the_middle_of_a_chunk_is_not_hidden_by_a_good_last_command(self):
        # the incident: lftp exits 0 when only the LAST command succeeded
        self.e.stage(pack())
        rc, out = self.e.run('upload', FAKE_FAIL=json.dumps({'README.md': 99}))
        self.assertEqual(rc, 1, out)
        self.assertIn('README.md', out)

    def test_dry_run_changes_nothing_and_prints_plan(self):
        self.e.stage(pack())
        self.e.remote({'mods/old.jar': 'x', 'config/c.toml': 'c'})
        for cmd in ('wipe', 'upload'):
            rc, out = self.e.run(cmd, DRY_RUN='true')
            self.assertEqual(rc, 0, out)
            self.assertIn('DRY RUN', out)
        self.assertEqual(self.e.read('mods/old.jar'), 'x')
        self.assertIsNone(self.e.read('README.md'))

    def test_wipe_removes_pack_dirs_not_world_and_survives_a_stubborn_dir(self):
        self.e.stage(pack())
        self.e.remote({'mods/a.jar': '1', 'config/x.toml': '1', 'tacz/LICENSE.txt': 'l', 'world/level.dat': 'W',
                       'kubejs/s.js': 's'})
        rc, out = self.e.run('wipe', FAKE_NOWIPE=json.dumps(['tacz']))
        self.assertEqual(rc, 0, out)                       # leftovers are a warning, never a failed run
        self.assertIn('WIPE', out.upper())
        self.assertIsNone(self.e.read('mods/a.jar'))
        self.assertEqual(self.e.read('world/level.dat'), 'W')
        self.assertEqual(self.e.read('tacz/LICENSE.txt'), 'l')
        self.assertIn('::warning::', out)
        rc, out = self.e.run('wipe', WIPE_WORLD='true')
        self.assertIsNone(self.e.read('world/level.dat'))

    def test_save_missing_keep_file_is_only_a_warning(self):
        rc, out = self.e.run('save', KEEP_FILES='mods/tfgcrew-1.20.1-0.2.0.jar config/tfgcrew-common.toml')
        self.assertEqual(rc, 0, out)
        self.assertIn('::warning::', out)
        self.assertEqual(open(os.path.join(self.e.cwd, 'keep/.saved')).read(), '')

    def test_save_network_error_aborts_before_any_delete(self):
        self.e.remote({'mods/tfgcrew-1.20.1-0.2.0.jar': 'JAR'})
        rc, out = self.e.run('save', KEEP_FILES='mods/tfgcrew-1.20.1-0.2.0.jar',
                             FAKE_GETERR=json.dumps(['mods/tfgcrew-1.20.1-0.2.0.jar']))
        self.assertEqual(rc, 1, out)
        self.assertIn('Nothing was deleted', out)

    def test_version_marker_read_error_is_not_treated_as_none(self):
        rc, out = self.e.run('current', FAKE_GETERR=json.dumps(['.tfg-version']))
        self.assertEqual(rc, 3, out)
        self.e.remote({'.tfg-version': '0.13.15\n'})
        rc, out = self.e.run('current')
        self.assertEqual(open(os.path.join(self.e.cwd, 'current.txt')).read(), '0.13.15')
        os.remove(os.path.join(self.e.srv, '.tfg-version'))
        rc, out = self.e.run('current')
        self.assertEqual((rc, open(os.path.join(self.e.cwd, 'current.txt')).read()), (0, 'none'))

    def test_save_wipe_upload_restore_fixes_marker_roundtrip(self):
        self.e.stage(pack())
        self.e.remote({'mods/tfgcrew-1.20.1-0.2.0.jar': 'CREWJAR', 'config/tfgcrew-common.toml': 'secret=1',
                       'mods/stale.jar': 's', 'server.properties': 'motd=hi\nenable-query=true\nlevel-type=default\n',
                       'config/voicechat/voicechat-server.properties': 'port=24454\nother=1\n', '.keep-files': '# c\nmods/extra.jar\n',
                       'mods/extra.jar': 'EX'})
        kp = dict(KEEP_FILES='mods/tfgcrew-1.20.1-0.2.0.jar config/tfgcrew-common.toml')
        self.assertEqual(self.e.run('save', **kp)[0], 0)
        self.assertEqual(self.e.run('wipe')[0], 0)
        self.assertIsNone(self.e.read('mods/stale.jar'))
        rc, out = self.e.run('upload', FAKE_FAIL=json.dumps({'config/a.toml': 99}))
        self.assertEqual(rc, 1, out)                       # upload failed ...
        rc, out = self.e.run('fixes')                      # ... fixes and put-back still work
        self.assertEqual(rc, 0, out)
        rc, out = self.e.run('restore')
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.e.read('mods/tfgcrew-1.20.1-0.2.0.jar'), 'CREWJAR')
        self.assertEqual(self.e.read('mods/extra.jar'), 'EX')
        self.assertEqual(self.e.read('config/tfgcrew-common.toml'), 'secret=1')
        sp = self.e.read('server.properties').split('\n')
        self.assertEqual(sp[:1], ['motd=hi'])
        self.assertIn('enable-query=false', sp)
        self.assertEqual(sp[-2], 'level-type=tfc:overworld')
        self.assertEqual(sp.count('enable-query=false'), 1)
        self.assertEqual(self.e.read('config/voicechat/voicechat-server.properties'), 'port=-1\n')   # config/ was wiped, so the fix recreates the file
        self.assertEqual(self.e.read('eula.txt'), 'eula=true\n')
        self.assertEqual(self.e.read('config/modernfix-mixins.properties'), 'mixin.perf.clear_mixin_classinfo=false\n')
        rc, out = self.e.run('marker', LATEST='0.13.17')
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.e.read('.tfg-version'), '0.13.17')

    def test_fix_is_skipped_when_file_unreadable(self):
        self.e.remote({'server.properties': 'motd=precious\n'})
        rc, out = self.e.run('fixes', FAKE_GETERR=json.dumps(['server.properties']))
        self.assertEqual(rc, 1, out)
        self.assertEqual(self.e.read('server.properties'), 'motd=precious\n')

    def test_no_secret_in_output(self):
        self.e.stage(pack())
        rc, out = self.e.run('upload', DRY_RUN='true')
        self.assertNotIn('secretpw', out)

    def test_pick_release(self):
        rels = [{'tag_name': t, 'draft': False, 'prerelease': pre, 'html_url': 'u',
                 'assets': [{'name': 'TerraFirmaGreg-Modern-%s-curseforge.zip' % t, 'browser_download_url': 'c'},
                            {'name': 'TerraFirmaGreg-Modern-%s-serverpack.zip' % t, 'browser_download_url': 's'}]}
                for t, pre in (('0.13.18-rc1', True), ('0.13.17', False), ('0.13.16', False), ('0.13.15', False))]
        r, a = tfg_ftp.pick_release(rels)
        self.assertEqual((r['tag_name'], a['name']), ('0.13.17', 'TerraFirmaGreg-Modern-0.13.17-serverpack.zip'))
        self.assertEqual(tfg_ftp.pick_release(rels, '0.13.15')[0]['tag_name'], '0.13.15')
        self.assertEqual(tfg_ftp.pick_release(rels, 'v0.13.16')[0]['tag_name'], '0.13.16')
        self.assertEqual(tfg_ftp.pick_release(rels, r'^0\.13\.1[56]$')[0]['tag_name'], '0.13.16')
        with self.assertRaises(SystemExit):
            tfg_ftp.pick_release(rels, '0.13.1')            # a plain version is exact, not a prefix


if __name__ == '__main__':
    unittest.main(verbosity=1)
