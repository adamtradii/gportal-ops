# gportal-ops

Operations for the G-Portal Minecraft server. Workflows (Actions tab -> Run workflow):

- **deploy-tfg.yml** - install/update TerraFirmaGreg from its official GitHub
  release (wipe_old=true also deletes the old pack + world first)
- **deploy-starwars.yml** - restore the Star Wars Galaxy RPG pack (syncs the
  `server/` tree from the star-wars-galaxy-rpg repo; run it from that repo,
  kept here as reference)
- **server-file.yml** - get/append/put/delete a single server file over FTP
- **fetch-logs.yml** - print the server's latest.log tail + newest crash report

Secrets required (Settings -> Secrets and variables -> Actions):
GPORTAL_FTP_SERVER, GPORTAL_FTP_USERNAME, GPORTAL_FTP_PASSWORD, GPORTAL_FTP_PORT

G-Portal FTP quirks, learned the hard way: no NLST (avoid lftp mirror),
no SITE CHMOD (--no-perms), drops long sessions (chunk + retry + put -c).
