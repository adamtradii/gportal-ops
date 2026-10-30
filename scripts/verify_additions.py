#!/usr/bin/env python3
"""Re-verify pack/crownfall/additions.json against the real files (stdlib only).

For every entry: download `url` (retry x3), check size and sha1 against the lock, then open the jar and read
META-INF/mods.toml: it must be a Forge mod (modLoader javafml, NOT a NeoForge-only neoforge.mods.toml), the declared
mod_id must be present, its `minecraft` dependency range must cover 1.20.1, its `forge` dependency range must cover
47.4.13, and every mandatory dependency must be provided by another entry in the lock or by TFG (pack/crownfall/tfg_mod_ids.json).

usage:
  verify_additions.py [--lock pack/crownfall/additions.json] [--tfg-ids pack/crownfall/tfg_mod_ids.json]
                      [--only mod_id ...] [--cache DIR] [--no-requires]
exit 0 = all entries verified, 1 = at least one problem (every problem is printed with the entry name).
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
import tomllib
import urllib.request
import zipfile

MC_VERSION = "1.20.1"
FORGE_VERSION = "47.4.13"
IMPLICIT = {"minecraft", "forge", "java", "neoforge"}


def vkey(v):
    """Comparable key for a dotted/dashed version string: numeric parts compare as ints, others as text."""
    parts = []
    for p in v.replace("-", ".").replace("+", ".").replace("_", ".").split("."):
        if p == "":
            continue
        parts.append((0, int(p), "") if p.isdigit() else (1, 0, p.lower()))
    return parts


def in_range(version, rng):
    """Maven/Forge version range check. '' / '*' / a bare version (soft requirement) accept anything."""
    rng = (rng or "").strip()
    if rng in ("", "*"):
        return True
    if rng[0] not in "[(":
        return True
    # split "[a,b),[c,d)" into single ranges
    singles, depth, cur = [], 0, ""
    for ch in rng:
        cur += ch
        if ch in "[(":
            depth += 1
        if ch in "])":
            depth -= 1
            if depth == 0:
                singles.append(cur.strip(", "))
                cur = ""
    vk = vkey(version)
    for s in singles:
        lo_incl, hi_incl = s[0] == "[", s[-1] == "]"
        body = s[1:-1]
        if "," not in body:      # [1.20.1] exact
            if vk == vkey(body.strip()):
                return True
            continue
        lo, hi = [x.strip() for x in body.split(",", 1)]
        ok = True
        if lo:
            ok &= vk >= vkey(lo) if lo_incl else vk > vkey(lo)
        if hi:
            ok &= vk <= vkey(hi) if hi_incl else vk < vkey(hi)
        if ok:
            return True
    return False


def sha1_of(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def download(url, dest, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gportal-ops-verify/1"})
            with urllib.request.urlopen(req, timeout=300) as r, open(dest + ".part", "wb") as f:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            os.replace(dest + ".part", dest)
            return None
        except Exception as e:  # network, 404, ...
            last = e
            time.sleep(2 * (i + 1))
    return "download failed: %s" % last


def read_mods_toml(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    if "META-INF/mods.toml" not in names:
        return None, ("no META-INF/mods.toml (NeoForge-only jar)" if "META-INF/neoforge.mods.toml" in names else "no mods.toml")
    return tomllib.loads(z.read("META-INF/mods.toml").decode("utf-8", "replace")), None


def check_toml(toml, entry):
    """Problems with the mods.toml of one entry; also returns the mandatory non-implicit deps."""
    errs, req = [], []
    if toml.get("modLoader") != "javafml":
        errs.append("modLoader is %r, not javafml" % toml.get("modLoader"))
    ids = [m.get("modId") for m in toml.get("mods", [])]
    if entry["mod_id"] not in ids:
        errs.append("mod_id %r not in mods.toml (has %s)" % (entry["mod_id"], ids))
    deps = []
    for mid in ids or [entry["mod_id"]]:
        deps += (toml.get("dependencies") or {}).get(mid, [])
    seen = {}
    for d in deps:
        seen.setdefault(d.get("modId"), d)
    mc, fg = seen.get("minecraft"), seen.get("forge")
    if mc and not in_range(MC_VERSION, mc.get("versionRange", "")):
        errs.append("minecraft range %s does not cover %s" % (mc.get("versionRange"), MC_VERSION))
    if fg and not in_range(FORGE_VERSION, fg.get("versionRange", "")):
        errs.append("forge range %s does not cover %s" % (fg.get("versionRange"), FORGE_VERSION))
    if toml.get("loaderVersion") and not in_range("47", toml["loaderVersion"]) and not in_range(FORGE_VERSION, toml["loaderVersion"]):
        errs.append("loaderVersion %s excludes Forge 47" % toml["loaderVersion"])
    for mid, d in seen.items():
        mandatory = d.get("mandatory", d.get("type") == "required")
        if mandatory and mid not in IMPLICIT and mid not in ids:
            req.append(mid)
    return errs, req


def verify_entry(entry, path):
    errs = []
    if not os.path.exists(path):
        return ["file missing"], []
    size = os.path.getsize(path)
    if entry.get("size") is not None and size != entry["size"]:
        errs.append("size %d != lock %d" % (size, entry["size"]))
    if sha1_of(path) != entry["sha1"]:
        errs.append("sha1 %s != lock %s" % (sha1_of(path), entry["sha1"]))
    try:
        toml, err = read_mods_toml(path)
    except zipfile.BadZipFile:
        return errs + ["not a zip/jar"], []
    if err:
        return errs + [err], []
    e2, req = check_toml(toml, entry)
    return errs + e2, req


def main(argv=None):
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    ap.add_argument("--lock", default=os.path.join(root, "pack/crownfall/additions.json"))
    ap.add_argument("--tfg-ids", default=os.path.join(root, "pack/crownfall/tfg_mod_ids.json"))
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--cache", default=None, help="directory to keep downloads (default: temp dir)")
    ap.add_argument("--no-requires", action="store_true", help="skip the dependency-provided check")
    a = ap.parse_args(argv)
    lock = json.load(open(a.lock))
    tfg_ids = set()
    if os.path.exists(a.tfg_ids):
        tfg_ids = set(json.load(open(a.tfg_ids)))
    provided = {m["mod_id"] for m in lock["mods"]} | tfg_ids | IMPLICIT
    cache = a.cache or tempfile.mkdtemp(prefix="verify-additions-")
    os.makedirs(cache, exist_ok=True)
    bad = 0
    for m in lock["mods"]:
        if a.only and m["mod_id"] not in a.only:
            continue
        dest = os.path.join(cache, m["filename"])
        errs = []
        if not (os.path.exists(dest) and sha1_of(dest) == m["sha1"]):
            e = download(m["url"], dest)
            if e:
                errs.append(e)
        req = []
        if not errs:
            errs, req = verify_entry(m, dest)
        if not a.no_requires:
            for r in req:
                if r not in provided:
                    errs.append("mandatory dependency %r is not provided by TFG or another entry" % r)
            for r in m.get("requires", []):
                if r not in provided:
                    errs.append("requires %r not provided" % r)
        if errs:
            bad += 1
            print("FAIL %s (%s): %s" % (m["name"], m["filename"], "; ".join(errs)))
        else:
            print("ok   %s (%s)" % (m["name"], m["filename"]))
    print("%d problem(s)" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
