#!/usr/bin/env python3
"""Regenerate pack/crownfall/additions.json from SPEC (below) and a directory holding the downloaded jars.

usage: build_crownfall_lock.py <jar_dir> <version> [--group core|all]
Each SPEC row names a CurseForge file (project id, file id, filename); size and sha1 are read from the real jar in <jar_dir>,
the mod_id and mandatory dependencies from its META-INF/mods.toml. Jars come from
https://edge.forgecdn.net/files/<fileId div 1000>/<fileId mod 1000>/<urlencoded filename> (see scripts/verify_additions.py).
"""
import hashlib, json, os, sys, tomllib, urllib.parse, zipfile

# (group, name, cf_project_id, cf_file_id, filename, side, why)
SPEC = [
 ("core", "MineColonies", 245506, 9058213, "minecolonies-1.20.1-1.1.1301.jar", "both", "Colonies, citizens, builders: the base of starbases/colonies. Newest non-snapshot 1.20.1 release (Oct 4 2026)."),
 ("core", "Structurize", 298744, 8610456, "structurize-1.20.1-1.0.818.jar", "both", "MineColonies blueprint/placement library; MineColonies 1301 needs >=1.0.818."),
 ("core", "BlockUI", 522992, 7541343, "blockui-1.20.1-1.0.193.jar", "both", "MineColonies/Structurize GUI library (MineColonies needs >=1.0.190-snapshot)."),
 ("core", "Minecolonies: War 'N Taxes", 1129258, 8761258, "WarNTaxes-5.0.9.jar", "both", "Wars, taxes, vassals for colonies. CurseForge 5.0.9 (Aug 2026) is newer than Modrinth minecolony-tax-addon 3.2.2."),
 ("core", "MineColonies: War 'n Nobility", 1580789, 9294588, "warnnobility-forge-1.1.4-1.20.1-java17.jar", "both", "Feudal ranks/counties on top of War 'N Taxes."),
 ("core", "Caravans & Convoys - Automatic Trade", 1599431, 9294591, "caravansconvoys-forge-1.0.14-1.20.1-java17.jar", "both", "Docks + horse-drawn wagon trade routes."),
 ("core", "Hundred Years Warfare", 1286643, 8688814, "HundredYearsWar-0.7.1r-fix1-1.20.1-forge.jar", "both", "NPC armies / RTS control (12.8 MB; mixins hit ChunkMap/ServerPlayer, see AUDIT risks)."),
 ("core", "SDM Shop", 948942, 7935087, "SDMShop-forge-1.20.1-7.2.2.jar", "both", "Shop GUI/economy front end."),
 ("core", "SDM Economy", 1102542, 6689080, "SDMEconomy-1.20.1-forge-2.2.0.jar", "both", "Currency ledger library (SDM Shop 7.2.2 needs >=2.2.0)."),
 ("core", "SDM UI Lib", 1095061, 6086204, "sdm_ui_lib-forge-1.20.1-1.8.3.jar", "both", "UI library for SDM Shop (needs >=1.20.1-1.8.3)."),
 ("core", "Epic Knights: Shields, Armor and Weapons", 509041, 8931670, "epic-knights-1.20.1-forge-10.15.jar", "both", "Medieval armour/weapons."),
 ("core", "Epic Knights: Addon", 925866, 7667762, "epic-knights-addon-1.20.x-forge-2.6.jar", "both", "Epic Knights addon (needs Epic Knights >=10.8)."),
 ("core", "Small Ships", 450659, 9206001, "smallships-2.0.2-forge-1.20.1.jar", "both", "Vanilla-friendly ships with cannons."),
 ("core", "Trotting Wagons", 1313811, 6916809, "trotting_wagons-1.0.4.jar", "both", "Horse-drawn wagons."),
 ("core", "Butchercraft", 265715, 6058842, "butchercraft-2.4.1.jar", "both", "Semi-realistic butchering (standalone; Survivor's Butchery integration skipped, see AUDIT)."),
 ("more", "MineColonies Tweaks", 975812, 8600075, "MineColonies_Tweaks-1.20.1-2.107-all.jar", "both", "Citizen tools/config tweaks; hard requirement of MineColonies Compatibility."),
 ("more", "Compatibility addon for MineColonies", 1006214, 9254868, "MineColonies_Compatibility-1.20.1-2.142.jar", "both", "MineColonies compat with other mods (Butchercraft etc.)."),
 ("more", "Palette Swap for MineColonies", 1567948, 8353116, "structurizereplacements-1.20.1-0.4.67.jar", "both", "Re-palette blueprints per block."),
 ("more", "TownTalk", 900364, 5355511, "towntalk-1.20.1-1.1.0.jar", "both", "Citizen voice lines (49 MB)."),
 ("more", "Lychee", 567403, 8030949, "Lychee-1.20.1-Forge-5.2.1.jar", "both", "[optional] Recipe engine, mandatory dependency of Hardrock Tools & Materials."),
 ("more", "Stone Crude Age (HardRock Tools & Materials)", 948055, 6060647, "htm-1.20.1-forge-1.0.8.jar", "both", "[optional] Crude-age tools; required by Animals Trap."),
 ("more", "Animals Trap", 954291, 4997023, "AnimalTrap-1.20.1-forge-1.0.1.jar", "both", "[optional] Small animal traps (beta, Dec 2023)."),
 ("more", "Animals Trap for TFC", 954871, 4997031, "AnimalTrapTFC-1.20.1-forge-1.0.1.jar", "both", "[optional] TFC animals for the traps (beta, Dec 2023)."),
 ("more", "TFC More Items", 1189837, 6304834, "tfc_items-1.20.1-forge-1.1.1.jar", "both", "[optional] Extra TFC items; required by Spindles TFC."),
 ("more", "Spindles TFC", 1258816, 6749542, "TFC_Spindles-1.20.1-forge-1.0.1.jar", "both", "[optional] Spinning for TFC."),
 ("more", "TFC Ore Washing", 959262, 6145630, "tfc-ore-washing-1.20.1-forge-1.0.6.jar", "both", "[optional] Ore washing for TFC."),
 ("more", "Farmers TFC", 1318733, 8700140, "farmerstfc-2.1.7-1.20.1.jar", "both", "[optional] Farmer's Delight x TFC integration (TFC API check OK vs bundled 3.2.28)."),
 ("more", "Farmer's Delight", 398521, 8765179, "FarmersDelight-1.20.1-1.3.4.jar", "both", "[optional] Cooking/farming; required by Farmers TFC."),
 ("more", "Neruina - Ticking Entity Fixer", 851046, 9220570, "neruina-3.3.5+1.20.1-forge.jar", "both", "[optional] Catches ticking-entity exceptions instead of crashing (beta)."),
 ("more", "spark", 361579, 4738952, "spark-1.10.53-forge.jar", "both", "Server profiler for lag diagnosis."),
]
PROVIDED_BY_TFG = {"architectury", "cloth_config", "ftblibrary", "tfc", "firmalife", "domum_ornamentum", "forge", "minecraft"}

def sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def main():
    jars, version = sys.argv[1], sys.argv[2]
    group = sys.argv[sys.argv.index("--group") + 1] if "--group" in sys.argv else "all"
    mods = []
    rows = [r for r in SPEC if group == "all" or r[0] == "core"]
    ids = {}
    for g, name, pid, fid, fn, side, why in rows:
        p = os.path.join(jars, fn)
        t = tomllib.loads(zipfile.ZipFile(p).read("META-INF/mods.toml").decode("utf-8", "replace"))
        mid = t["mods"][0]["modId"]
        ids[name] = mid
        req = []
        for d in (t.get("dependencies") or {}).get(mid, []):
            if d.get("mandatory") and d["modId"] not in ("forge", "minecraft") and d["modId"] not in req:
                req.append(d["modId"])
        mods.append({"name": name, "mod_id": mid, "side": side, "source": "curseforge", "cf_project_id": pid, "cf_file_id": fid,
                     "modrinth_project": None, "modrinth_version_id": None, "filename": fn,
                     "url": "https://edge.forgecdn.net/files/%d/%d/%s" % (fid // 1000, fid % 1000, urllib.parse.quote(fn)),
                     "sha1": sha1(p), "size": os.path.getsize(p), "requires": req, "why": why})
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pack/crownfall")
    dec = json.load(open(os.path.join(base, "decisions.json")))
    skipped = [{"name": d["name"].strip(), "cf_project_id": d["cf_project_id"], "reason": d["reason"]} for d in dec if d["decision"] in ("skip", "pending")]
    in_tfg = [{"name": d["name"].strip(), "tfg_file": d["tfg_file"]} for d in dec if d["decision"] == "already_in_tfg"]
    out = {"pack_name": "TFG Crownfall", "additions_version": version,
           "base": {"repo": "TerraFirmaGreg-Team/Modpack-Modern", "tracks": "latest release"},
           "mods": mods, "skipped": skipped, "already_in_tfg": in_tfg}
    json.dump(out, open(os.path.join(base, "additions.json"), "w"), indent=1, ensure_ascii=False)
    print(len(mods), "mods")

if __name__ == "__main__":
    main()
