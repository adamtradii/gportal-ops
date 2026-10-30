# TFG Crownfall pack - running notes (branch feat/crownfall-pack)

Owner request 2026-10-29 22:45 PT: "Add the crownfall mods and TFG into a new pack and configure the autoupdater using that pack."
Keep this file current after every step (the owner switches Claude subscriptions; whoever picks up reads this, CLAUDE.md, then continues).

## Verified facts (2026-10-30, from the real sources)
- TFG release assets (TerraFirmaGreg-Team/Modpack-Modern, tag has NO leading v): `TerraFirmaGreg-Modern-<ver>-serverpack.zip`,
  `TerraFirmaGreg-Modern-<ver>-curseforge.zip` (checked 0.13.17: both 200, a made-up name 404). The release API is NOT reachable from the
  cloud sandbox (403), the tag list (git ls-remote) and the download URLs are.
- serverpack zip (535 MB, 4943 entries): NO root folder; mods/ (217 jars), config/, defaultconfigs/, kubejs/, tacz/, DiscordIntegration-Data/,
  plus top-level server_starter.conf, start_server.sh/.bat, minecraft_server.jar, server.properties, README.md, server-icon.png, forge-auto-install.txt.
- curseforge zip (198 MB): `manifest.json` {minecraft{version 1.20.1, modLoaders[forge-47.4.13]}, manifestType, manifestVersion 1, name, version, author,
  files[276 x {projectID,fileID,required}], overrides:"overrides"} + overrides/ (only 2 jars in overrides/mods: steampowered, cc-tweaked).
- MineColonies data lives in `<world>/minecolonies/` (colonies.dat, <dim>/colony<N>.dat, backups): read from ldtteam/minecolonies
  `BackUpHelper` (LevelResource.ROOT + "minecolonies"), version/main @ 61292848. So it is inside `world/`, which only wipe_world=true touches.

## What is built
- `scripts/build_pack.py` (stdlib): `version` | `server` | `client`. Pack version = `<tfg tag>+cf<additions_version>` (PACK=tfg: plain tag).
  All downloads verified (size + sha1, refuse on mismatch, all problems reported at once, before any FTP step). Duplicate mod ids (mods.toml
  [[mods]] modId) between TFG's jars and ours are refused (two jars of one mod crash the boot). Client: manifest.json name "TFG Crownfall",
  version, files += CurseForge ids; mods with no CF ids go to overrides/mods; overrides overlay.
- `scripts/tfg_ftp.py`: `release` also writes tfg_tag.txt + client_asset_url.txt; `wipe` reads `wipe-extra.txt` (folders the overrides bring,
  validated by `valid_wipe_dir`: never world*, logs, minecolonies, libraries, backups, DiscordIntegration-Data, hidden, nested).
- Tests: `python3 scripts/test_build_pack.py` (21), `python3 scripts/test_tfg_ftp.py` (13).

## Also built (2026-10-30)
- `scripts/refresh_additions.py` ("keep the mods up to date"): Modrinth newest Forge 1.20.1 RELEASE per mod (candidate must pass mods.toml checks:
  Forge jar, loaderVersion covers 47, forge/minecraft dependency ranges cover 47.4.13 / 1.20.1; a failing newer file is skipped with its reason and
  the next older one tried). CurseForge-id mods stay pinned (no key on a runner) unless `pack/crownfall/cf-updates.json`
  `{"<mod_id>": {"cf_file_id","filename","url","sha1","size"}}` gives a newer one. Bumps `additions_version` (integer +1) only on change; prints
  `CHANGED <mod> [side]: old -> new`. Tests: `python3 scripts/test_refresh_additions.py` (10).
- `build_pack.py` also refuses a missing mandatory dependency of an ADDED jar (jar-in-jar libraries count: `tfc` is inside TerraFirmaGreg-Core;
  client-side-only deps are ignored on the server; `SKIP_DEP_CHECK=true` overrides).
- `.github/workflows/tfg-update.yml`: inputs `pack`, `refresh_mods` (no skip_lab: removed 2026-10-30 on the lead's review); steps Refresh mods -> Check (release, version, current) -> Build
  server payload (build_pack.py server) -> save/wipe/upload/fixes/restore/marker. The refresh gate sits between Refresh and Check (below).
  Schedule untouched (frozen).
- `.github/workflows/pack-release.yml`: client zip -> release `crownfall-<tfg>+cf<n>` of this repo.
- End-to-end rehearsal on the REAL TFG 0.13.17 assets (local): server tree 4248 TFG files + 1 fake mod, 217 jars; client zip 188 MB, manifest
  "TFG Crownfall" 0.13.17+cf1 with TFG's 276 CurseForge files; dependency `tfc` resolved through the jar-in-jar inside TerraFirmaGreg-Core.

## NOT done / next
1. Merge feat/crownfall-lock (additions.json) and this branch to main (lead). Nothing here has run on GitHub Actions yet.
2. First dispatch (read-only): see "Exact first dry run" below. Then `pack-release.yml` with dry_run=true to prove the client zip builds on a runner.
3. Boot test of the combined pack (lab) BEFORE the real install; VS2/Eureka-style overlaps (Kotlin For Forge, Ad Astra) belong to the mod-list work.
4. New mods may need extra server fixes (config lines): add them to FIXES in scripts/tfg_ftp.py (+ CLAUDE.md table).
5. Schedule stays frozen; unfreeze only on the owner's word.

## Exact first dry run (after both branches are on main)
Actions -> "TFG auto-update" -> Run workflow: `pack=crownfall`, `dry_run=true`, `refresh_mods=false`, force=false, wipe_world=false,
version_match empty. Expect: "pack version ... 0.13.17+cf<n>", every mod "mod <file> <side>" downloaded + checked, "staged ... TFG files",
"WOULD DELETE (dry run)", the upload plan listing chunks with the mod jars, "WOULD PATCH" fixes, no change on the server.
Then the same with `refresh_mods=true` to see what the refresh would change (a dry run only reports the change, pushes nothing).

## Commands
- Tests: `python3 scripts/test_tfg_ftp.py && python3 scripts/test_build_pack.py && python3 scripts/test_refresh_additions.py`
- Local rehearsal: in a scratch dir put tfg_tag.txt, asset_url.txt, client_asset_url.txt (file:// or https URLs) and
  pack/crownfall/additions.json, then `python3 scripts/build_pack.py version|server|client` (env PACK, ADDITIONS, OVERRIDES, MIN_STAGED_FILES, SLEEP).

## Refresh gate (lead review 2026-10-30)
If `refresh_additions.py` changes the lock in a run, the step "Push the refreshed lock to a review branch and stop" commits ONLY
`pack/crownfall/additions.json` to a new branch `pack-refresh/<UTC date>-<run id>` (`[skip ci]`, GITHUB_TOKEN contents: write, plain push, never
main), prints `REFRESH BRANCH: ...` (log + step summary), and every later step is skipped: no FTP read, no wipe, no upload, no marker. The install
only ever uses the lock on the dispatched ref. To ship a refresh: lab-test the branch's lock -> merge the branch to main -> run "TFG auto-update"
(refresh_mods=false). The old "commit the refreshed lock to main after the install" step and `skip_lab` are gone. A dry run reports the change,
pushes nothing and rehearses on the refreshed lock. Exact first dry run is unchanged except there is no `skip_lab` input.
