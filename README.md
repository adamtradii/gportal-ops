# gportal-ops

Operations for the G-Portal Minecraft server (Actions tab -> pick workflow -> Run workflow).

- **tfg-update.yml** - TFG auto-update: checks TerraFirmaGreg's official releases
  daily; installs new versions without touching the world. Manual inputs:
  force=true (redeploy same version), wipe_world=true (ONLY when a TFG update
  requires a fresh world), version_match (pin a release).
- **server-file.yml** - get/append/put/delete one server file over FTP.
- **fetch-logs.yml** - print the server's latest.log tail + newest crash report.

Secrets (Settings -> Secrets and variables -> Actions -> Repository secrets):
GPORTAL_FTP_SERVER, GPORTAL_FTP_USERNAME, GPORTAL_FTP_PASSWORD, GPORTAL_FTP_PORT

G-Portal FTP quirks, learned the hard way: no NLST (never use lftp mirror),
no SITE CHMOD (skip permissions), drops long sessions (chunked uploads,
retries, put -c resume). The Star Wars pack restore lives in the
star-wars-galaxy-rpg repo (deploy-server.yml there).

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
