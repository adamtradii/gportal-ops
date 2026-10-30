#!/usr/bin/env python3
"""Test for verify_additions.py: runs it on fake local jars (file:// URLs). usage: python3 scripts/test_verify_additions.py"""
import hashlib
import json
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_additions as v

FORGE_TOML = '''modLoader="javafml"
loaderVersion="[47,)"
license="MIT"
[[mods]]
modId="fakemod"
version="1.0"
[[dependencies.fakemod]]
modId="forge"
mandatory=true
versionRange="[47,)"
side="BOTH"
[[dependencies.fakemod]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.21)"
side="BOTH"
[[dependencies.fakemod]]
modId="otherlib"
mandatory=true
versionRange="[1,)"
side="BOTH"
'''


def make_jar(path, toml, name="META-INF/mods.toml"):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(name, toml)
        z.writestr("fake/Thing.class", b"\xca\xfe")


def entry(path, **kw):
    e = {"name": "Fake", "mod_id": "fakemod", "side": "both", "source": "curseforge", "cf_project_id": 1, "cf_file_id": 2,
         "modrinth_project": None, "modrinth_version_id": None, "filename": os.path.basename(path), "url": "file://" + path,
         "sha1": hashlib.sha1(open(path, "rb").read()).hexdigest(), "size": os.path.getsize(path), "requires": ["otherlib"], "why": "t"}
    e.update(kw)
    return e


def run(lock_mods, tfg_ids):
    d = tempfile.mkdtemp()
    lock = os.path.join(d, "lock.json")
    ids = os.path.join(d, "ids.json")
    json.dump({"mods": lock_mods}, open(lock, "w"))
    json.dump(tfg_ids, open(ids, "w"))
    return v.main(["--lock", lock, "--tfg-ids", ids, "--cache", os.path.join(d, "cache")])


def main():
    # version ranges
    assert v.in_range("1.20.1", "[1.20,1.21)") and v.in_range("1.20.1", "[1.20.1]") and v.in_range("1.20.1", "[1.20.1, 1.20.2)")
    assert not v.in_range("1.20.1", "[1.21,)") and not v.in_range("1.20.1", "(,1.20)") and v.in_range("1.20.1", "1.19")
    assert v.in_range("47.4.13", "[47.1.0,)") and not v.in_range("47.4.13", "[48,)") and v.in_range("47.4.13", "[46.0.1,),")
    assert v.in_range("1.20.1", "[1.19,1.20),[1.20.1,1.21)")
    d = tempfile.mkdtemp()
    good = os.path.join(d, "good.jar")
    make_jar(good, FORGE_TOML)
    assert run([entry(good)], ["otherlib"]) == 0, "good jar must verify"
    assert run([entry(good)], []) == 1, "unprovided mandatory dependency must fail"
    assert run([entry(good, sha1="0" * 40)], ["otherlib"]) == 1, "sha1 mismatch must fail"
    assert run([entry(good, size=1)], ["otherlib"]) == 1, "size mismatch must fail"
    neo = os.path.join(d, "neo.jar")
    make_jar(neo, FORGE_TOML.replace("javafml", "javafml"), name="META-INF/neoforge.mods.toml")
    assert run([entry(neo)], ["otherlib"]) == 1, "NeoForge-only jar must fail"
    wrongmc = os.path.join(d, "wrongmc.jar")
    make_jar(wrongmc, FORGE_TOML.replace("[1.20.1,1.21)", "[1.21,1.22)"))
    assert run([entry(wrongmc)], ["otherlib"]) == 1, "minecraft range without 1.20.1 must fail"
    wrongid = os.path.join(d, "wrongid.jar")
    make_jar(wrongid, FORGE_TOML)
    assert run([entry(wrongid, mod_id="nope")], ["otherlib"]) == 1, "wrong mod_id must fail"
    missing = entry(good, url="file://" + os.path.join(d, "does-not-exist.jar"), filename="missing.jar")
    assert run([missing], ["otherlib"]) == 1, "unreachable url must fail"
    print("test_verify_additions: all checks passed")


if __name__ == "__main__":
    main()
