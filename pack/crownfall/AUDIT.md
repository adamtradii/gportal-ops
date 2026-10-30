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

## Status after push 1 (additions_version 1 = core gameplay set, 15 mods, verified by scripts/verify_additions.py: real download, size, sha1, Forge mods.toml, MC 1.20.1, Forge 47.4.13, deps provided)
Core set in the lock: MineColonies 1.1.1301, Structurize 1.0.818, BlockUI 1.0.193, War 'N Taxes 5.0.9, War 'n Nobility 1.1.4, Caravans & Convoys 1.0.14,
Hundred Years Warfare 0.7.1r-fix1, SDM Shop 7.2.2 / Economy 2.2.0 / UI Lib 1.8.3, Epic Knights 10.15 + Addon 2.6, Small Ships 2.0.2, Trotting Wagons 1.0.4, Butchercraft 2.4.1.
Version 2 will add (SPEC rows with group "more" in scripts/build_crownfall_lock.py): MineColonies Tweaks 2.107 + Compatibility 2.142 (MineColonies API check
still running), Palette Swap, TownTalk, Lychee/HTM/Animals Trap(+TFC), TFC More Items, Spindles, Ore Washing, Farmers TFC + Farmer's Delight, Neruina, spark. Multi-Piston: pending.
Regenerate: `python3 scripts/build_crownfall_lock.py <jar_dir> <version> [--group core]` (reads pack/crownfall/decisions.json for skipped/already_in_tfg).
Per-mod decisions for all 128: pack/crownfall/decisions.json. TFG mod id list: pack/crownfall/tfg_mod_ids.json (used by the verifier).

## Coins / currency (lead's note + what the Crownfall configs show)
- TFG coins come from BOTH the GT forming press (nugget + cylinder casting mold) and Create pressing (nugget -> coin: copper/wrought iron/steel/gold/brass/zinc/blue steel), createdeco coins.
- SDM Economy is a LEDGER currency (config/SDMEconomy/currencies/currencies.data: id `sdmcoin`, symbol, default value), it needs no item.
- War 'N Taxes pays taxes into that ledger (`SDMCurrencyName = "sdmcoin"`) and has `CurrencyItemName = "minecraft:emerald"` (default) for the item form: set it to a TFG coin item id
  (lead to name the createdeco coin id) or leave ledger-only. War 'n Nobility `buyin_item` was set to minecraft:structure_void in Crownfall so rank cannot be bought.
- Crownfall made its own coin items with KubeJS (kubejs:penny/mark/noble, startup script crownfall_coins.js) and re-pointed vanilla iron/gold/emerald recipe inputs of caravansconvoys,
  warnnobility and hundred_years_war to `#c:ingots/wrought_iron` / `#c:ingots/gold` (kubejs/server_scripts/crownfall_economy.js): TFG has the same problem (no vanilla iron), so those recipes need a KubeJS patch.

## Checklist
- [x] Crownfall id mapping, CurseForge file lists, candidate jars + mods.toml
- [x] TFC API resolve vs bundled TFC 3.2.28: Farmers TFC OK (112 refs, 0 missing); TFC Astikor Carts 1.1.9 OK; Survivor's Abilities OK (but skipped for mixin overlap); Butchercraft,
      HTM, TFC More Items, Spindles, Ore Washing, Animals Trap TFC reference no net/dries007/tfc classes at all (data-driven; data ids untested until boot).
      NOTE: lab/api_check.py's resolver reported false MISSING for constructors (javap names them by class, the checker looked for <init>, and kept quotes on the name): fixed in the copy used here.
- [ ] MineColonies API resolve for MC addons (running; javap on the 78 MB jar is slow)
- [ ] Mixin overlap table (done for includes in the core set, see below)
- [x] additions.json v1, verify_additions.py + test
