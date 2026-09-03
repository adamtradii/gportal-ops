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

## Current state (2026-09-03)
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
- `tfg-update.yml` - daily 09:17 UTC + manual. Compares `.tfg-version` to the
  newest non-prerelease release; on change (or `force=true`) deletes ONLY
  `mods config kubejs defaultconfigs scripts tacz patchouli_books`, uploads the
  new pack (listing-free chunked lftp), then re-applies every fix below.
  Never touches the world unless `wipe_world=true` is passed by a human.
  Skips the pack's `server.properties`, `user_jvm_args.txt`, installers,
  launch scripts and `libraries/` (G-Portal owns the runtime).
  A full force reinstall takes ~25 min.
- `server-file.yml` - `get` / `append` / `put` / `delete` one file.
  `append` is a SET: a `key=value` line replaces an existing line with that
  key; other lines are appended once. Use `\n` in `content` for several lines.
- `fetch-logs.yml` - prints `logs/latest.log` tail (400 lines), newest crash
  report, and a root `ls`. Job logs over ~70 KB come back as a file from the
  MCP tool; parse `logs_content` with python and grep for
  `ERROR|Exception|Stopping server|Done \(`.

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
