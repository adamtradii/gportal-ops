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
