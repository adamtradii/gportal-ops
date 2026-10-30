#!/usr/bin/env python3
"""Tests for scripts/refresh_additions.py against a fake Modrinth API served by a local http.server.
Run: python3 scripts/test_refresh_additions.py"""
import functools, hashlib, http.server, json, os, shutil, sys, tempfile, threading, unittest, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_pack as bp  # noqa: E402
import refresh_additions as ra  # noqa: E402


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def jar(path, mid, forge='[47,)', mc='[1.20.1,1.21)', mandatory_dep=None, neoforge=False):
    toml = 'modLoader="javafml"\nloaderVersion="[47,)"\n[[mods]]\nmodId="%s"\n' % mid
    toml += '[[dependencies.%s]]\nmodId="forge"\nmandatory=true\nversionRange="%s"\nside="BOTH"\n' % (mid, forge)
    toml += '[[dependencies.%s]]\nmodId="minecraft"\nmandatory=true\nversionRange="%s"\nside="BOTH"\n' % (mid, mc)
    if mandatory_dep:
        toml += '[[dependencies.%s]]\nmodId="%s"\nmandatory=true\nversionRange="[1,)"\nside="BOTH"\n' % (mid, mandatory_dep)
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('META-INF/neoforge.mods.toml' if neoforge else 'META-INF/mods.toml', toml)
        z.writestr('x.class', os.path.basename(path))


def sha1(p):
    with open(p, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


class T(unittest.TestCase):
    def setUp(self):
        self.w = tempfile.mkdtemp()
        self.srv = os.path.join(self.w, 'srv')
        os.makedirs(self.srv)
        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=self.srv))
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = 'http://127.0.0.1:%d/' % self.httpd.server_address[1]
        ra.API = self.base.rstrip('/')
        os.environ['SLEEP'] = '0'
        self.cwd = os.getcwd()
        os.chdir(self.w)
        self.addCleanup(self.cleanup)

    def cleanup(self):
        os.chdir(self.cwd)
        self.httpd.shutdown(); self.httpd.server_close()
        shutil.rmtree(self.w, True)

    def version(self, slug, vid, number, fn, date, vtype='release', mid=None, wrong_sha=False, **jk):
        p = os.path.join(self.srv, fn)
        jar(p, mid or slug, **jk)
        d = os.path.join(self.srv, 'v2/project', slug)
        os.makedirs(d, exist_ok=True)
        lst = json.load(open(os.path.join(d, 'version'))) if os.path.exists(os.path.join(d, 'version')) else []
        lst.append({'id': vid, 'version_number': number, 'version_type': vtype, 'date_published': date,
                    'loaders': ['forge'], 'game_versions': ['1.20.1'],
                    'files': [{'primary': True, 'filename': fn, 'url': self.base + fn, 'size': os.path.getsize(p),
                               'hashes': {'sha1': '0' * 40 if wrong_sha else sha1(p)}}]})
        json.dump(lst, open(os.path.join(d, 'version'), 'w'))
        return p

    def lock(self, mods):
        a = {'pack_name': 'TFG Crownfall', 'additions_version': '1', 'base': {}, 'mods': mods, 'skipped': [], 'already_in_tfg': []}
        json.dump(a, open('additions.json', 'w'), indent=2)
        return 'additions.json'

    def entry(self, slug, fn, vid, side='both', cf=None):
        p = os.path.join(self.srv, fn)
        return {'name': slug.title(), 'mod_id': slug, 'side': side, 'source': 'curseforge' if cf else 'modrinth',
                'cf_project_id': cf[0] if cf else None, 'cf_file_id': cf[1] if cf else None, 'modrinth_project': slug,
                'modrinth_version_id': vid, 'filename': fn, 'url': self.base + fn, 'sha1': sha1(p),
                'size': os.path.getsize(p), 'requires': [], 'why': 'w'}

    def test_newest_release_is_adopted_prerelease_skipped_version_bumped(self):
        self.version('alpha', 'v1', '1.0', 'alpha-1.0.jar', '2026-01-01')
        self.version('alpha', 'v2', '1.1', 'alpha-1.1.jar', '2026-02-01')
        self.version('alpha', 'v3', '1.2-beta', 'alpha-1.2-beta.jar', '2026-03-01', vtype='beta')
        self.version('cfmod', 'c1', '1.0', 'cfmod-1.0.jar', '2026-01-01')
        self.version('cfmod', 'c2', '2.0', 'cfmod-2.0.jar', '2026-02-01')
        path = self.lock([self.entry('alpha', 'alpha-1.0.jar', 'v1'), self.entry('cfmod', 'cfmod-1.0.jar', 'c1', cf=(9, 90))])
        r = ra.run(path)
        self.assertEqual([(c['name'], c['old'], c['new']) for c in r['changes']], [('Alpha', 'alpha-1.0.jar', 'alpha-1.1.jar')])
        self.assertEqual((r['old_version'], r['new_version']), ('1', '2'))
        d = json.load(open(path))
        m = d['mods'][0]
        self.assertEqual((m['filename'], m['modrinth_version_id'], m['sha1'], m['url']),
                         ('alpha-1.1.jar', 'v2', sha1(os.path.join(self.srv, 'alpha-1.1.jar')), self.base + 'alpha-1.1.jar'))
        self.assertEqual(d['mods'][1]['filename'], 'cfmod-1.0.jar')      # CurseForge ids: pinned
        self.assertEqual(d['additions_version'], '2')
        self.assertTrue(any('Cfmod' in p and 'pinned' in p.lower() for p in r['pinned']), r['pinned'])
        self.assertIn('CHANGED Alpha', ra.report(r))

    def test_nothing_new_leaves_the_file_byte_identical(self):
        self.version('alpha', 'v1', '1.0', 'alpha-1.0.jar', '2026-01-01')
        path = self.lock([self.entry('alpha', 'alpha-1.0.jar', 'v1')])
        before = open(path).read()
        r = ra.run(path)
        self.assertEqual((r['changes'], r['new_version']), ([], '1'))
        self.assertEqual(open(path).read(), before)

    def test_incompatible_newer_files_are_skipped_with_reasons(self):
        self.version('alpha', 'v1', '1.0', 'alpha-1.0.jar', '2026-01-01')
        self.version('alpha', 'v2', '1.1', 'alpha-1.1.jar', '2026-02-01', neoforge=True)
        self.version('alpha', 'v3', '1.2', 'alpha-1.2.jar', '2026-03-01', forge='[48,)')
        self.version('alpha', 'v4', '1.3', 'alpha-1.3.jar', '2026-04-01', mc='[1.21,1.22)')
        self.version('alpha', 'v5', '1.4', 'alpha-1.4.jar', '2026-05-01', wrong_sha=True)
        path = self.lock([self.entry('alpha', 'alpha-1.0.jar', 'v1')])
        r = ra.run(path)
        self.assertEqual(r['changes'], [])
        txt = ' | '.join(r['warnings'])
        for needle in ('NeoForge', 'needs Forge [48,)', 'needs Minecraft [1.21,1.22)', 'sha1'):
            self.assertIn(needle, txt)
        self.assertEqual(json.load(open(path))['mods'][0]['filename'], 'alpha-1.0.jar')

    def test_falls_back_to_the_next_older_compatible_file(self):
        self.version('alpha', 'v1', '1.0', 'alpha-1.0.jar', '2026-01-01')
        self.version('alpha', 'v2', '1.1', 'alpha-1.1.jar', '2026-02-01')
        self.version('alpha', 'v3', '1.2', 'alpha-1.2.jar', '2026-03-01', forge='[48,)')
        r = ra.run(self.lock([self.entry('alpha', 'alpha-1.0.jar', 'v1')]))
        self.assertEqual(r['changes'][0]['new'], 'alpha-1.1.jar')
        self.assertTrue(any('1.2' in w for w in r['warnings']))

    def test_api_failure_keeps_pinned_file_with_warning(self):
        self.version('alpha', 'v1', '1.0', 'alpha-1.0.jar', '2026-01-01')
        e = self.entry('alpha', 'alpha-1.0.jar', 'v1')
        e['modrinth_project'] = 'no-such-project'
        r = ra.run(self.lock([e]))
        self.assertEqual(r['changes'], [])
        self.assertTrue(any('404' in w for w in r['warnings']), r['warnings'])

    def test_cf_updates_file_moves_a_curseforge_mod_and_is_verified(self):
        self.version('cfmod', 'c1', '1.0', 'cfmod-1.0.jar', '2026-01-01')
        jar(os.path.join(self.srv, 'cfmod-2.0.jar'), 'cfmod')
        new = {'cfmod': {'cf_file_id': 91, 'filename': 'cfmod-2.0.jar', 'url': self.base + 'cfmod-2.0.jar',
                         'sha1': sha1(os.path.join(self.srv, 'cfmod-2.0.jar')), 'size': os.path.getsize(os.path.join(self.srv, 'cfmod-2.0.jar'))}}
        path = self.lock([self.entry('cfmod', 'cfmod-1.0.jar', 'c1', cf=(9, 90))])
        r = ra.run(path, cf_updates=new)
        m = json.load(open(path))['mods'][0]
        self.assertEqual((m['cf_file_id'], m['cf_project_id'], m['filename']), (91, 9, 'cfmod-2.0.jar'))
        new['cfmod']['sha1'] = '2' * 40
        self.lock([self.entry('cfmod', 'cfmod-1.0.jar', 'c1', cf=(9, 90))])
        r = ra.run(path, cf_updates=new)
        self.assertEqual(r['changes'], [])
        self.assertTrue(any('refused' in w for w in r['warnings']))

    def test_dry_write_false_does_not_touch_the_file(self):
        self.version('alpha', 'v1', '1.0', 'alpha-1.0.jar', '2026-01-01')
        self.version('alpha', 'v2', '1.1', 'alpha-1.1.jar', '2026-02-01')
        path = self.lock([self.entry('alpha', 'alpha-1.0.jar', 'v1')])
        before = open(path).read()
        r = ra.run(path, write=False)
        self.assertEqual(len(r['changes']), 1)
        self.assertEqual(open(path).read(), before)

    def test_bump(self):
        self.assertEqual([ra.bump(x) for x in ('1', '9', '2026.3', 'rc')], ['2', '10', '2026.4', 'rc.1'])

    def test_main_writes_outputs(self):
        self.version('alpha', 'v1', '1.0', 'alpha-1.0.jar', '2026-01-01')
        self.version('alpha', 'v2', '1.1', 'alpha-1.1.jar', '2026-02-01')
        path = self.lock([self.entry('alpha', 'alpha-1.0.jar', 'v1')])
        os.environ.update(ADDITIONS=path, GITHUB_OUTPUT=os.path.join(self.w, 'out.txt'))
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ('ADDITIONS', 'GITHUB_OUTPUT')])
        self.assertEqual(ra.main(), 0)
        self.assertIn('changed=true', open(os.path.join(self.w, 'out.txt')).read())
        self.assertIn('CHANGED Alpha', open('refresh-report.md').read())

    def test_ranges(self):
        for spec, v, exp in (('[47,)', '47.4.13', True), ('[47.5,)', '47.4.13', False), ('[1.20.1,1.21)', '1.20.1', True),
                             ('[1.20,1.20.1)', '1.20.1', False), ('[1.20.1]', '1.20.1', True), ('[1.20.2]', '1.20.1', False),
                             ('1.20.1', '1.20.1', True), ('', '1', True), ('[1.19,1.19.4),[1.20,1.21)', '1.20.1', True)):
            self.assertEqual(bp.range_contains(spec, v), exp, spec)


if __name__ == '__main__':
    unittest.main(verbosity=1)
