# gportal-ops

Operations for the G-Portal Minecraft server (Actions tab -> pick workflow -> Run workflow).

- **tfg-update.yml** - pack update: installs the "TFG Crownfall" pack (TerraFirmaGreg + the Crownfall mods)
  without touching the world. Manual inputs: pack=crownfall|tfg (tfg = plain TerraFirmaGreg fall-back),
  dry_run=true (rehearsal, changes nothing), force=true (redeploy same version), wipe_world=true (ONLY when an
  update requires a fresh world), version_match (pin the TFG release), refresh_mods (look for newer mod files first),
  skip_lab (install a refreshed mod list without the lab test). The daily schedule is frozen.
- **pack-release.yml** - builds the player download (the TFG Crownfall client zip) and attaches it to a release here.
- **server-file.yml** - get/append/put/delete one server file over FTP.
- **fetch-logs.yml** - print the server's latest.log tail + newest crash report.

Secrets (Settings -> Secrets and variables -> Actions -> Repository secrets):
GPORTAL_FTP_SERVER, GPORTAL_FTP_USERNAME, GPORTAL_FTP_PASSWORD, GPORTAL_FTP_PORT

G-Portal FTP quirks, learned the hard way: no NLST (never use lftp mirror),
no SITE CHMOD (skip permissions), drops long sessions (chunked uploads,
retries, put -c resume). The Star Wars pack restore lives in the
star-wars-galaxy-rpg repo (deploy-server.yml there).

## Players: joining the TFG Crownfall server
1. Open this repo's **Releases** page (GitHub login needed, the repo is private) and download
   `TFG-Crownfall-<version>-client.zip` from the newest `crownfall-...` release. Do not unzip it.
2. CurseForge app -> Minecraft -> **Create Custom Profile** -> **Import** -> pick the zip.
   Let it download all mods, then Play. The profile is named "TFG Crownfall"; its version must match the server's.
3. After the server announces an update, download the newest release zip and import it again as a new profile.

## Known server fixes the updater re-applies
- **Simple Voice Chat port**: the default UDP 24454 is taken on the shared
  G-Portal host. The bind fails and the mod shuts the whole server down about
  1.5s after load-complete (looks like a clean stop, no crash report). Fix:
  `port=-1` in `config/voicechat/voicechat-server.properties` (share the game
  port) plus `enable-query=false` in `server.properties`, because query would
  bind that same UDP port.
- `mixin.perf.clear_mixin_classinfo=false` (ModernFix) - avoids the Greate
  mixin InjectionError during class-info clearing.
- `level-type=tfc:overworld`, `enable-rcon=true`, `eula=true`.
