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
