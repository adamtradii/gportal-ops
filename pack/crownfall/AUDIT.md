# Crownfall -> TFG mod audit (WORK IN PROGRESS, resume notes first)

Owner request 2026-10-29 22:45 PT: add Crownfall Kingdoms 2.0.5 mods + TFG into one pack. Target: Forge 1.20.1-47.4.13, TFG 0.13.17
(TFC fork bundled in TerraFirmaGreg-Core 0.9.31). Crownfall itself is NeoForge 1.21.1, so every mod needs a Forge 1.20.1 build.

## How to resume (state of the work)
- Crownfall manifest order == modlist.html order (index i of both lists is the same mod). Mapping + CurseForge file lists were built with
  api.cfwidget.com/<projectId> (works from the sandbox; gives file id, name, type, size, loader/mc tags). Downloads: forgecdn
  `https://edge.forgecdn.net/files/<id div 1000>/<id mod 1000>/<urlencoded filename>`.
- Each candidate jar is downloaded, sha1 computed, META-INF/mods.toml read (modLoader, deps, side), mixin configs and @Mixin targets parsed.
- TFG's own jars (216 non-client) were downloaded to compare mixin targets (TFC/GTCEu/Create/FTB/ModernFix/Krypton...).
- Still to do (see bottom checklist): TFC API resolve (api_check approach) for TFC addons, MineColonies-API resolve for MC addons,
  mixin overlap table, additions.json, verifier + test.

## Decisions so far (Crownfall index in brackets)
Legend: INCLUDE / SKIP(reason) / TFG (already in TFG, TFG's version kept). Evidence = what was read (mods.toml deps, CurseForge file list).

### Already in TFG (keep TFG's version)
Domum Ornamentum [1] (TFG 1.0.304-snapshot, satisfies MineColonies >=1.0.288), Simple Voice Chat, ArborFirmaCraft, Lootr, Crash Assistant, Puzzles Lib,
Euphoria Patches, FirmaLife, Block Runner, Astikor Carts TFC (TFG 1.1.8.3; Crownfall's 1.1.9 not taken), Drippy Loading Screen, AllTheLeaks, Rhino, Jade,
I Heart TFC, Roads and Roofs, TFC Vessel Tooltip, Astikor Carts Redux, TFCGenViewer, FTB Ranks/Quests/Teams/Library, TFC Support Indicator, FramedBlocks,
Curios, New Animals for TFC (resource pack), KubeJS, GeckoLib, Corpse, Konkrete, FerriteCore, Patchouli, TFC Aged Alcohol, Architectury, FancyMenu, KubeJS TFC,
Cloth Config, Melody, Embeddium, UniLib, Carry On, CraftPresence, Sophisticated Core, Mouse Tweaks, Barrels 2012, TerraFirmaCraft (bundled in TFG-Core),
TerraFirmaCraft AnvilHelper (TFG ships tfc-anvil-helper-patched).

### SKIP (reason)
- Cold Sweat, TFC Cold Sweat, TFC Textile (Cold Sweat Edition): overlap TFG-Core body temperature + tfc-ambiental-refreshed.
- Lithium: no Forge 1.20.1 build (Fabric/NeoForge only on CurseForge; TFG has radium-reforged as its Lithium port).
- Distant Horizons: owner-listed overlap/renderer; heavy on server, conflicts risk with Oculus/Embeddium.
- Connectivity: TFG ships packet-fixer + krypton-fnp (same job).
- JEI, Just Enough Breeding, MezzConfig: TFG uses EMI; JEI would duplicate.
- JourneyMap: TFG ships Xaero's minimap/world map. JourneyMap TFC Integration: no 1.20.1 build.
- Entity Model Features, Entity Texture Features, NeoOculus, Makeup shader: renderers/cosmetic; TFG has Oculus/Embeddium/ImmediatelyFast/EntityCulling.
- NeoForge-only / no 1.20.1 build on CurseForge (cfwidget file list has only 1.21.x): KubeJS Minecolonies Events, Better Advanced Tooltips, FirmaNutrition,
  TFC-MineCol-Compat, TFPRevivedCompat, TFCDraughtworks, TFC Registry API, Wary Predators for TFC, NeoOrigins, Configurable, Entity View Distance,
  Drippy Early Loading Module.
- Resource packs / shaders (not mods): Knight'sArmory32X32, Aures TFC Livestock Skins, TFC Ore Marker Expanded, MakeUp shader.
- Better Combat + playerAnimator: changes the combat system globally; the crew bodies use Player.attack; no 1.20.1 playerAnimator in the Forge list.
- Starter Kit + Collective: Starter Kit gives items on first login, crew fake players log in as new players.
- Simple Discord Link Bot + CraterLib: needs a bot token/config; crew already posts to Discord by webhook.
- Watut + CoroUtil, Explosive Enhancement, Clean Swing, RightClickHarvest, JamLib, Cupboard: cosmetic/QoL, not needed (JamLib only needed by RightClickHarvest).
- Better With MineColonies: 2023 build (1.20), stale vs MineColonies 1.1.1301.
- SDM Engine Core: SDM Shop 7.2.2 / SDM Economy 2.2.0 do not depend on it (read their mods.toml).

### INCLUDE (candidates, mods.toml read; final file picks in additions.json)
MineColonies 1.1.1301 (release), Structurize 1.0.818 (release), BlockUI 1.0.193 (release), Multi-Piston, MineColonies Tweaks 2.107, MineColonies
Compatibility 2.142 (hard-requires Tweaks >=2.107), Palette Swap (structurizereplacements 0.4.67), TownTalk, War 'N Taxes 5.0.9 (CurseForge, newer than
Modrinth 3.2.2), War 'n Nobility 1.1.4 (1.20.1 build exists; requires War N Taxes), Caravans & Convoys 1.0.14, Hundred Years Warfare 0.7.1r-fix1,
SDM Shop 7.2.2, SDM Economy 2.2.0, SDM UI Lib 1.8.3, Epic Knights 10.15 + Addon 2.6, Small Ships 2.0.2, Trotting Wagons 1.0.4, Butchercraft 2.4.1,
Hardrock Tools & Materials (htm 1.0.8, needs Lychee) + Lychee + Kiwi, Animals Trap (needs htm) + Animals Trap for TFC, Spindles TFC + TFC More Items,
TFC Ore Washing, Farmers TFC + Farmer's Delight, Neruina, spark.
PENDING: Survivor's Abilities + Survivor's Butchery (mixins hit TFC TFCFoodData/NutritionData/livestock classes that TFG-Core also patches - compare).

## Checklist
- [x] Crownfall id mapping, CurseForge file lists, candidate jars + mods.toml
- [ ] TFC API resolve vs bundled TFC 3.2.28 for TFC addons
- [ ] MineColonies API resolve for MC addons
- [ ] Mixin overlap vs TFG jars
- [ ] Coins/currency check for SDM Economy / War N Taxes (lead: TFG coins come from GT forming press AND Create pressing nugget->coin; createdeco coins)
- [ ] additions.json, verify_additions.py + test
