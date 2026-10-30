# HANDOFF: the TFG + Crownfall pack (lead notes, kept current)

Owner (Adam) 2026-10-29 PT, in order:
- 22:45 "Add the crownfall mods and TFG into a new pack and configure the autoupdater using that pack"
- ~22:50 "Make sure to keep constant notes so we can switch claude subs when you run out of usage"
- ~22:50 "Can you also create a new server pack and run the updater to keep the mods up to date and then update the server?"
Lead session: claude.ai/code session_01AJA3 (also runs the hourly crew report for adamtradii/tfgworkers).
Anyone picking this up: read this file, then gportal-ops/CLAUDE.md, then tfgworkers/docs/HANDOFF-2026-10-26.md (its Log).

## Verified facts (sources named)
- Crownfall Kingdoms = CurseForge project 1575866, latest file 9342058 "TFC Minecolonies.zip" (Crownfall 2.0.5, 2026-10-27),
  NeoForge 21.1.248 / MC 1.21.1, 128 mods. Download that worked from the sandbox: https://edge.forgecdn.net/files/9342/58/TFC%20Minecolonies.zip
  (the CDN path is fileID div 1000 / fileID mod 1000 / url-encoded filename). CurseForge site API /api/v1 = 403; Modrinth API works.
- Our server: TFG Modern 0.13.17, Forge 1.20.1-47.4.13, Java 17. TFG bundles its own TFC fork (3.2.28) inside TerraFirmaGreg-Core.
- Forge 1.20.1 builds exist (checked 2026-10-29): MineColonies minecolonies-1.20.1-1.1.1304-snapshot.jar (CF, newest release 1.1.1301),
  War N Taxes 3.2.2 (Modrinth minecolony-tax-addon), Caravans & Convoys caravansconvoys-forge-1.0.14-1.20.1-java17.jar (CF),
  Hundred Years Warfare 0.7.1r-fix1-1.20.1-forge (Modrinth), SDM Shop 1.20.1-7.2.2 (Modrinth), Epic Knights 10.15 (Modrinth),
  TFC Astikor Carts 1.1.9 (Modrinth). War 'n Nobility: no 1.20.1 page found.
- TFG's coins (pack clone kubejs/server_scripts/createdeco/recipes.js:326-360 + the LIVE recipe export, tfgworkers vps-check run 41008233559):
  createdeco:copper_coin, iron_coin (Wrought Iron), industrial_iron_coin (Steel), gold_coin, brass_coin, zinc_coin, netherite_coin (Blue Steel),
  each also *_coinstack (4 coins). Made from ONE nugget by create:pressing (Create mechanical press) or gtceu:forming_press (+ cylinder casting mold).
- Crownfall's own systems (read from its overrides): pennies/marks/nobles (custom KubeJS items, minted on a TFC anvil: silver ingot -> 9 marks,
  gold -> 9 nobles), SDM Shop/Economy balance + exchange, War 'N Taxes (town hall 4 +2/level, tavern 6 +1/level, houses 2/level per real day;
  military upkeep), Caravans & Convoys (wagon repair 4 marks), Hundred Years Warfare raids/wars/sieges, ranks Outsider..Emperor, KubeJS scripts
  crownfall_minecolonies_tfc.js / crownfall_huts.js (huts from TFC materials), crownfall_classes.js, crownfall_origins.js, crownfall_seasons.js,
  crownfall_economy.js. Those scripts are KubeJS 1.21 (2101) and must be PORTED to TFG's KubeJS 2001 (phase 2).

## Plan (status)
1. Mod audit + lock pack/crownfall/additions.json + AUDIT.md -- helper, gportal-ops branch feat/crownfall-lock. IN PROGRESS.
2. Pack builder (server tree + CurseForge-import client zip), updater (tfg-update.yml input pack=crownfall|tfg, marker "<tfg>+cf<n>"),
   mod refresh (scripts/refresh_additions.py), pack-release.yml -- helper, gportal-ops branch feat/crownfall-pack (notes docs/CROWNFALL-PACK.md). IN PROGRESS.
3. Boot test: tfgworkers lab-fullpack.yml input `additions` (lab/packs/crownfall-additions.json) -- helper, tfgworkers branch feat/crownfall-lab. IN PROGRESS.
4. Lead: review + merge 1 and 2 into gportal-ops main; copy the lock into tfgworkers lab/packs/; dispatch the lab; read the boot log.
5. tfg-update.yml dry_run=true pack=crownfall; then the OWNER STOPS THE SERVER; real run; tfgworkers deploy-gportal puts the crew mod back if missing;
   owner starts; fetch-logs.yml for 'Done (' and no mod errors; publish the client zip (pack-release.yml) and give Adam the link.
6. Phase 2: port Crownfall's KubeJS (huts from TFC materials, coins/minting decision, classes/races) and configs (War 'N Taxes numbers etc.).
Never: run the live updater without the lab boot passing; turn on the daily schedule (.github/TFG_AUTO_UPDATE stays off unless the owner says).

## Log (PT)
- 2026-10-29 22:50 lead: helpers started for steps 1-3; this file created.
