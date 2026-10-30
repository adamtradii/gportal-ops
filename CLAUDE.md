# CLAUDE.md - gportal-ops handoff (read this first)

Ops for the owner's G-Portal Minecraft server, which now runs **TerraFirmaGreg
(TFG) Modern**. The Star Wars pack this box used to run lives in the sibling repo
`star-wars-galaxy-rpg` (dormant; `deploy-server.yml` there restores it).
Owner: Adam (adamtradii), a GitHub novice who mostly works from a phone. Keep
instructions short, tell him exactly which button to press, and never make him
merge a PR for an ops change - this repo is pushed to `main` directly.

## HARD RULES (owner directives, earned the hard way)
1. **Never guess external identifiers.** Verify every slug, owner/repo, asset
   name, API path, config key and version with a real lookup BEFORE shipping.
   If it cannot be verified, say so and make the change fail safely.
2. **First-contact automation gets one shot.** Front-load retries, resume,
   defensive defaults, dry-run paths and failure output that prints next steps.
   Five sequential fix-and-rerun cycles on this server each cost the owner a
   round trip; he considers that unacceptable.
3. **Diagnose from evidence, not pattern-matching.** Fetch the log
   (`fetch-logs.yml`) before proposing any fix. Three earlier "fixes" (Forge
   version, query/rcon, a supervisor-timeout theory) were wrong because the
   real cause was never read out of the log.
4. Never put the FTP password anywhere but repository secrets. Never publish
   the Star Wars repo (it carries third-party jars).

## Current state (2026-10-30): the pack is "TFG Crownfall" (TFG + Crownfall mods); updater still frozen
Owner 2026-10-29 22:45 PT: "Add the crownfall mods and TFG into a new pack and configure the autoupdater using that pack."
Running notes (what is verified, what is next, exact commands): **docs/CROWNFALL-PACK.md**.
- **Pack = TFG's serverpack + `pack/crownfall/additions.json` mods (side both|server) + `pack/crownfall/overrides/`.** Built by
  `scripts/build_pack.py` (tests: `python3 scripts/test_build_pack.py`). The lock (`additions.json`) is written by the mod-list work
  (branch feat/crownfall-lock); every jar is downloaded from its `url` and checked against `size` + `sha1` (REFUSED on mismatch), two jars
  of one mod id or a missing mandatory dependency of an added mod are refused, all BEFORE the first FTP step.
- **Marker / pack version = `<tfg tag>+cf<additions_version>`** (e.g. `0.13.17+cf1`) in `.tfg-version` (same file as before). A change
  of EITHER the TFG release or `additions_version` installs. `pack=tfg` (fall-back) writes the plain tag, so switching packs reinstalls.
- **Inputs of `tfg-update.yml`:** `dry_run`, `version_match` (TFG tag, no leading v), `force`, `wipe_world`, plus NEW `pack` =
  crownfall (default) | tfg and `refresh_mods` (default true; manual runs of the crownfall pack only): `scripts/refresh_additions.py` looks
  for newer Forge 1.20.1 Modrinth files (CurseForge-id mods stay pinned unless `pack/crownfall/cf-updates.json` gives a newer file).
- **Refresh gate (a refreshed mod must pass the boot test before players see it).** If the refresh CHANGES the lock, the run pushes the
  refreshed `additions.json` to a NEW branch `pack-refresh/<UTC date>-<run id>` (never main), prints the branch name and STOPS before any
  server step (not even an FTP read). The install only ever uses the lock on the dispatched ref (main). Flow: lead lab-tests that branch's
  lock, merges it to main, then runs "TFG auto-update" again (refresh_mods=false, or true: an unchanged lock goes straight through).
  There is no path that installs a refresh from the run that found it, and nothing commits to main from the workflow. A dry run only
  reports the change (pushes nothing) and rehearses on the refreshed lock.
- **Fall back to plain TFG:** run "TFG auto-update" with `pack=tfg` (and `refresh_mods=false`). It wipes the same folders and installs the
  TFG serverpack; folders that only the Crownfall overrides brought (see `wipe-extra.txt` in the run's earlier log) are not known to it
  and stay until removed by hand.
- **Wipe list** = `mods config kubejs defaultconfigs scripts tacz patchouli_books` + any other top-level folder the overrides bring
  (`wipe-extra.txt`, validated: never `world*`, `logs`, `crash-reports`, `libraries`, `backups`, `minecolonies`, `DiscordIntegration-Data`,
  hidden or nested names; a bad name aborts before any delete). **MineColonies colony data is in `<world>/minecolonies/`** (colonies.dat,
  per-dimension colony<N>.dat, backups; ldtteam/minecolonies `BackUpHelper`, `LevelResource.ROOT`), i.e. inside `world/`: it survives every
  run except `wipe_world=true`, which now prints that warning.
- **Client:** workflow `pack-release.yml` (manual; `tfg_version` latest|tag, `dry_run`) builds TFG's `-curseforge.zip` with manifest name
  "TFG Crownfall", version `<tfg>+cf<n>`, the CurseForge ids of the added mods (Modrinth-only mods as jars in `overrides/mods`) and the overrides,
  and attaches `TFG-Crownfall-<tfg>-cf<n>-client.zip` to release `crownfall-<tfg>+cf<n>` of THIS (private) repo.
- **Verified TFG assets (0.13.17):** `TerraFirmaGreg-Modern-<ver>-serverpack.zip` (no root folder: mods/ config/ kubejs/ defaultconfigs/
  tacz/ ...) and `TerraFirmaGreg-Modern-<ver>-curseforge.zip` (manifest.json + overrides/). The release API 403s from the cloud sandbox;
  tags (`git ls-remote`) and `releases/download/...` URLs work.
- **Schedule still FROZEN** (`.github/TFG_AUTO_UPDATE` = off). The refresh never runs on the schedule.

## Earlier state (2026-10-27): INCIDENT + updater frozen (v2 updater, still how the FTP half works)
- **Incident.** Unattended `tfg-update.yml` runs 40356210574 (10-26, ->0.13.16) and 40530320802 (10-27 15:22-15:57 UTC,
  0.13.15 -> 0.13.17) wiped `mods config ...`, then failed the upload step, so "Re-apply server fixes", "Put back the
  saved files" (crew mod + `config/tfgcrew-common.toml`) and the version marker were SKIPPED. Marker still says 0.13.15
  while the server holds a (nearly complete) 0.13.17 with no crew mod, no voicechat/modernfix/server.properties fixes.
- **Root cause (from the job logs).** `put -c` onto a remote file that already exists in full ends in
  `put: stage/x: file size increased during transfer` (xaeroworldmap/yet_another_config_lib failed on tries 2-3 only,
  after try 1 had uploaded them complete; tacz/* and five top-level files failed on try 1 because they were already
  there: tacz survived the wipe in both runs, README.md, server-icon.png, server_starter.conf, forge-auto-install.txt and
  DiscordIntegration-Data/Messages.toml are never wiped at all). **lftp's exit status is the status of the LAST command
  only**: the 10-27 chunk 0000 (five such errors, last put fine) reported "done (try 1)", chunk 0005 failed only because
  its last file (tacz/ulv_guns.zip) was one of them. So most of the pack did upload; the five top-level files were never
  refreshed; and a resume onto a SMALLER stale file would have silently appended (corrupted) data. The wipe step
  (`|| true`, no output) took 11 min and was never checked.
- **Fix (v2 updater).** All FTP logic is `scripts/tfg_ftp.py` (tests: `python3 scripts/test_tfg_ftp.py`, real lftp
  against a temp dir with the incident's failures injected). Upload = `rm -f` exact name + PLAIN `put` (never `-c`);
  failures read from lftp's own `put:` lines, retried per file x3, a failed chunk no longer stops the run; read-back
  verify of a sample. Wipe is verified (listing, else get-probes) and retried x3, leftovers are a warning. Fixes, crew-mod
  put-back run after ANY upload outcome (`if: always()`); the version marker is written only if upload AND fixes
  succeeded. A transient FTP error is never read as "file absent" (version marker, keep files, server.properties).
  A keep-file that is not on the server is only a warning. `concurrency` group stops two runs overlapping.
- **FROZEN.** The daily schedule skips unless `.github/TFG_AUTO_UPDATE` says `on` (default `off`): the crew mod is pinned
  to a pack version (tfgworkers/CLAUDE.md). Manual "Run workflow" always works.
- **Inputs.** `dry_run=true` (read-only rehearsal: prints the plan, changes nothing), `version_match` (plain version =
  exact tag; TFG tags have no `v`: `0.13.17`; otherwise a regex), `force=true` (reinstall although the marker matches),
  `wipe_world`.
- **Owner decision 2026-10-27 16:25 PT: finish 0.13.17** (no rollback). Real run is dispatched by the lead after the
  owner stops the server; tfgworkers' deploy-gportal then puts the crew mod back (it is not on the server).
- Idea not built: upload to `*.new` folders and swap by rename (seconds of mixed state instead of ~40 min); needs a
  rename probe on G-Portal FTP first.

## Earlier state (2026-09-03)
- Server: `us2092751.g-portal.game`, game port **26305** (TCP; UDP shared with
  voice chat), rcon 26295, 14 GB RAM, Java 17, Forge **1.20.1-47.4.13**
  (pinned by TFG's pakku-lock; do not move it).
- Installed pack: **TFG Modern 0.13.9** from GitHub releases
  (`TerraFirmaGreg-Team/Modpack-Modern`, asset
  `TerraFirmaGreg-Modern-<ver>-serverpack.zip`). Marker file on the server:
  `.tfg-version`. Players install the matching
  `TerraFirmaGreg-Modern-<ver>-curseforge.zip` via the CurseForge app (Import).
- Last boot before the fix (log fetched 2026-09-03): the pack loads fully in
  ~150 s, then Simple Voice Chat fails to bind UDP 24454 ("Address already in
  use" - another tenant on the shared host) and shuts the server down. Fix
  applied and read back: `port=-1` in
  `config/voicechat/voicechat-server.properties` and `enable-query=false` in
  `server.properties`. **The boot after this fix has not been observed yet.**
  Next step: owner presses Start, then run `fetch-logs.yml` and confirm
  `Done (...)!` with no `Stopping server` after it.
- Open question: whether G-Portal forwards UDP on 26305 (needed for voice to
  actually connect). Server stability does not depend on it.

## Workflows (dispatch from Actions tab, or via the GitHub MCP
`actions_run_trigger` with ref=main; the cloud sandbox cannot reach FTP,
CurseForge, Modrinth or modrepo.de directly - GitHub Actions is the only plane)
- `pack-release.yml` - builds + publishes the Crownfall CLIENT zip (see Current state). `docs/CROWNFALL-PACK.md` has the commands.
- `tfg-update.yml` - FROZEN daily 09:17 UTC schedule (see Current state) + manual. Installs the pack chosen by `pack`
  (crownfall default = TFG + Crownfall mods, or plain tfg). Compares `.tfg-version` to the pack version of the
  newest non-prerelease TFG release (+ `+cf<additions_version>`); on change (or `force=true`) deletes ONLY
  `mods config kubejs defaultconfigs scripts tacz patchouli_books` (+ the overrides' own top-level folders), uploads the
  new pack (listing-free chunked lftp), then re-applies every fix below.
  Never touches the world unless `wipe_world=true` is passed by a human.
  Skips the pack's `server.properties`, `user_jvm_args.txt`, installers,
  launch scripts and `libraries/` (G-Portal owns the runtime).
  A full force reinstall takes ~25-45 min. FTP code: `scripts/tfg_ftp.py`.
- `server-file.yml` - `get` / `append` / `put` / `delete` one file.
  `append` is a SET: a `key=value` line replaces an existing line with that
  key; other lines are appended once. Use `\n` in `content` for several lines.
- `fetch-logs.yml` - prints `logs/latest.log` tail (400 lines), newest crash
  report, and a root `ls`. Job logs over ~70 KB come back as a file from the
  MCP tool; parse `logs_content` with python and grep for
  `ERROR|Exception|Stopping server|Done \(`.

## Crew mod survives updates (2026-10-13)
tfgworkers' crew mod lives in `mods/` and `config/`, which an update wipes. The updater saves every path in
`KEEP_FILES` (workflow env) plus the server's `.keep-files` (written by tfgworkers' deploy-gportal) before the wipe and
puts them back after, read back and compared. Until 2026-10-12 the version marker went up with `put -c`: the old
file ("0.13.9" + newline) was the same size as "0.13.10", the resume sent nothing, the marker never changed, and
EVERY daily run reinstalled 0.13.10 - deleting the crew mod each time. The marker is now a plain put, verified.

## Fixes the updater re-applies (all verified against primary sources)
| file | line | why |
|---|---|---|
| config/voicechat/voicechat-server.properties | `port=-1` | default UDP 24454 is taken on the host; bind failure shuts the server down |
| server.properties | `enable-query=false` | query binds UDP on the game port; the mod's own config says sharing it with voice "may crash the server" |
| server.properties | `enable-rcon=true` | harmless; panel injects rcon.port/password |
| server.properties | `level-type=tfc:overworld` | must exist before the first world generation |
| config/modernfix-mixins.properties | `mixin.perf.clear_mixin_classinfo=false` | Greate `whenItemHeld` InjectionError during ModernFix class-info clearing |
| eula.txt | `eula=true` | a fresh G-Portal install ships none; without it Java never launches |

## G-Portal facts (observed, not documentation)
- FTP: needs `set ftp:ssl-allow yes`; no NLST (lftp `mirror` and `ls`-based
  logic fail on some dirs - upload with generated `mkdir -pf` + `put -c`
  scripts fed on stdin, never `-f` after the host); no SITE CHMOD
  (`ftp:use-site-chmod no`); drops long sessions (chunk ~120 MB, retry x3).
- The panel rewrites `server.properties` on every start (injects server-ip,
  server-port, query.port, rcon.port, rcon.password) but preserves custom keys.
- Changing the Forge version on the Modification screen triggers a
  reinstall that WIPES the directory and, once, left the Forge runtime broken
  (Java never launched, `logs/` never created, Console blank, panel "Failed").
  **Verify Game Files** (Game server files page) repaired that without
  touching our files. **Wipe Server** is the day-one reset - avoid.
- "Restart for update" toggle on that page lets G-Portal move the Forge
  version on its own; owner was told to turn it OFF.
- Server root = FTP root. Forge runtime is outside the FTP-visible tree.
- Panel Console is blank whenever Java never launched; a blank console after
  Verify Game Files + Start means a G-Portal support ticket, not a file fix.

## Failure signatures -> meaning
- No `logs/` dir after Start: Java never launched -> Verify Game Files, then
  check `eula.txt` exists.
- `Done (...)` then `Stopping server` ~1 s later, no crash report: a mod
  called shutdown - grep the 30 lines before `Stopping server` (voicechat was
  the culprit; a new one would show there too).
- `InjectionError ... greate$whenItemHeld`: modernfix fix missing.
- `550 path does not exists` on `config/...`: the directory was wiped -
  run `tfg-update.yml` with `force=true`.

## What NOT to do
- Do not re-enable `enable-query=true` (undoes the voice fix).
- Do not set `wipe_world=true` unless a TFG release note requires it and the
  owner agreed.
- Do not create a `run-ops.yml` that executes arbitrary branch scripts with
  the FTP secrets - the safety classifier refuses to commit it twice; owner
  was given the YAML to add himself if he wants it.
- Do not ask the owner to merge PRs here; push to `main`.

## If the server still dies after the voicechat fix
Fetch the log, find the first ERROR before `Stopping server`, and fix THAT
file with `server-file.yml`. If Java does not launch at all after Verify Game
Files, send the owner this ticket text for G-Portal support:
"Forge 1.20.1-47.4.13 server never starts Java: Start shows Failed within
seconds, Console stays blank, no logs/ directory is created. Verify Game
Files and Wipe Server were tried. Please check the base Forge runtime
provisioning for this server."
