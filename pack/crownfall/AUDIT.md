# Crownfall -> TFG mod audit (additions_version 2)

Owner request 2026-10-29 22:45 PT: add Crownfall Kingdoms 2.0.5 (NeoForge 1.21.1, CurseForge 1575866 / file 9342058, 128 mods) and TFG into one pack.
Target: Forge 1.20.1-47.4.13, TFG 0.13.17 (TFC 3.2.28 is a fork bundled inside TerraFirmaGreg-Core 0.9.31, jar-in-jar ids included).
Counts: **31 INCLUDE** (15 core in v1, 16 more in v2), **49 SKIP**, **48 already in TFG** (= 128).
Files: `additions.json` (the lock), `decisions.json` (all 128, machine readable), `tfg_mod_ids.json` (mod ids of the real 0.13.17 serverpack),
`scripts/build_crownfall_lock.py` (SPEC table -> lock; regenerate with `python3 scripts/build_crownfall_lock.py <jar_dir> <version>`),
`scripts/verify_additions.py [--tfg-serverpack <TerraFirmaGreg-Modern-0.13.17-serverpack.zip>]` (re-downloads, size, sha1, Forge mods.toml, MC 1.20.1, Forge 47.4.13,
mandatory deps provided, no duplicate of a TFG mod id), test `python3 scripts/test_verify_additions.py`.

## How the data was gathered
- Crownfall manifest order == modlist.html order; project ids from the manifest. CurseForge file lists: api.cfwidget.com/<projectId> (file id, name, release type, size, loader/MC tags). Downloads: forgecdn
  `https://edge.forgecdn.net/files/<id div 1000>/<id mod 1000>/<urlencoded filename>`. Every INCLUDE jar was downloaded, sha1 computed, META-INF/mods.toml read (all `javafml`, none NeoForge-only).
- TFG side: pakku-lock.json for the first pass, then the REAL release asset `TerraFirmaGreg-Modern-0.13.17-serverpack.zip` (216 jars) for ids and mixin targets.
- Mixin targets: parsed from the class files (@Mixin value/targets) of every mixin config; compared with the targets of all 215 TFG jars (class level) and method level for the TFC food classes.
- TFC addons: `lab/api_check.py` approach (javap constant pool refs resolved against the classes in TerraFirmaGreg-Core 0.9.31). Copy used here fixes two checker bugs
  (constructor refs were reported MISSING because the name kept its quotes and javap names constructors by class).

## Decision per Crownfall mod (index = position in manifest/modlist)
- [0] Animals Trap (by sir_Robson): **INCLUDE** - AnimalTrap-1.20.1-forge-1.0.1.jar (CF 954291/4997023, animaltrap) requires=htm; [optional] Small animal traps (beta, Dec 2023).
- [1] Domum Ornamentum (by OrionOnline): **IN TFG** - TFG file: domum_ornamentum-1.20.1-1.0.304-snapshot-universal.jar
- [2] Cold Sweat (by Mikul): **SKIP** - overlaps TFG-Core body temperature (+ tfc-ambiental-refreshed); Cold Sweat would double-handle player temperature
- [3] Survivor's Abilities (by vomiter): **SKIP** - Survivor's Abilities mixes TFCFoodData.tick, ForgeEventHandler.onPlayerTick (overburdened), NutritionData; TFG-Core mixes the same methods (TFCFoodDataMixin, TFCFoodDataNutrientEffectsMixin, NutritionDataMixin, ForgeEventHandlerMixin). Survivor's Butchery hard-requires it
- [4] Simple Voice Chat (by henkelmax): **IN TFG** - TFG file: voicechat-forge-1.20.1-2.6.26.jar
- [5] ArborFirmaCraft (by Therighton): **IN TFG** - TFG file: afc-1.0.23-1.20.1.jar
- [6] SDM Engine Core (by Sixik): **SKIP** - not required: SDM Shop 7.2.2 / SDM Economy 2.2.0 mods.toml depend only on architectury, sdm_ui_lib, ftblibrary, sdmeconomy
- [7] KubeJS Minecolonies Events (by Lillo97): **SKIP** - NeoForge-only: CurseForge file list has only 1.21.x NeoForge files, no Forge 1.20.1 build
- [8] Small Ships (by talhanation): **INCLUDE** - smallships-2.0.2-forge-1.20.1.jar (CF 450659/9206001, smallships) requires=-; Vanilla-friendly ships with cannons.
- [9] Hundred Years Warfare (by ydmsama): **INCLUDE** - HundredYearsWar-0.7.1r-fix1-1.20.1-forge.jar (CF 1286643/8688814, hundred_years_war) requires=-; NPC armies / RTS control (12.8 MB; mixins hit ChunkMap/ServerPlayer, see AUDIT risks).
- [10] Lootr (Forge & NeoForge) (by Noobanidus): **IN TFG** - TFG file: lootr-forge-1.20-0.7.35.94.jar
- [11] Knight'sArmory32X32 (by Reymecos_TheArmorSmith): **SKIP** - resource pack / shader, not a mod (no 1.20.1 build or not needed; TFG ships its own resource packs)
- [12] Aures - TFC Livestock Skins (by BlackAuresArt): **SKIP** - resource pack / shader, not a mod (no 1.20.1 build or not needed; TFG ships its own resource packs)
- [13] Better Advanced Tooltips (by Lat): **SKIP** - NeoForge-only: CurseForge file list has only 1.21.x NeoForge files, no Forge 1.20.1 build
- [14] MezzConfig (by mezz): **SKIP** - TFG uses EMI; JEI would duplicate the recipe viewer (JEBr and MezzConfig exist only for JEI)
- [15] Stone Crude Age  - (HardRock Tools & Materials) (by sir_Robson): **INCLUDE** - htm-1.20.1-forge-1.0.8.jar (CF 948055/6060647, htm) requires=lychee; [optional] Crude-age tools; required by Animals Trap.
- [16] Trotting Wagons (by Favouriteless): **INCLUDE** - trotting_wagons-1.0.4.jar (CF 1313811/6916809, trotting_wagons) requires=-; Horse-drawn wagons.
- [17] FirmaNutrition (by JotredDev): **SKIP** - NeoForge-only: CurseForge file list has only 1.21.x NeoForge files, no Forge 1.20.1 build
- [18] Crash Assistant (by KostromDan): **IN TFG** - TFG file: CrashAssistant-forge-1.19-1.20.1-1.11.12.jar
- [19] Puzzles Lib (by Fuzs): **IN TFG** - TFG file: PuzzlesLib-v8.1.36-1.20.1-Forge.jar
- [20] Tweaks addon for MineColonies (by supernover0102): **INCLUDE** - MineColonies_Tweaks-1.20.1-2.107-all.jar (CF 975812/8600075, minecolonies_tweaks) requires=minecolonies; Citizen tools/config tweaks; hard requirement of MineColonies Compatibility.
- [21] Euphoria Patches (by SpacEagle17): **IN TFG** - TFG file: EuphoriaPatcher-1.10.5-r5.9.3-forge.jar
- [22] FirmaLife (by EERussianguy): **IN TFG** - TFG file: Firmalife-1.20.1-2.1.28.jar
- [23] TerraFirmaCraft AnvilHelper (by Fox2Code): **IN TFG** - TFG file: tfc-anvil-helper-patched (TFG patched build)
- [24] Distant Horizons: A Level of Detail mod (by James_Seibel): **SKIP** - renderer/LOD mod; heavy on a server, overlaps Oculus/Embeddium stack TFG ships; owner-listed overlap
- [25] Connectivity (by someaddon): **SKIP** - TFG ships packet-fixer + krypton-fnp which do the same job
- [26] Survivor's Butchery [TFC x Butchercraft] (by vomiter): **SKIP** - Survivor's Abilities mixes TFCFoodData.tick, ForgeEventHandler.onPlayerTick (overburdened), NutritionData; TFG-Core mixes the same methods (TFCFoodDataMixin, TFCFoodDataNutrientEffectsMixin, NutritionDataMixin, ForgeEventHandlerMixin). Survivor's Butchery hard-requires it
- [27] TFC Cold Sweat (by oatobaazul): **SKIP** - overlaps TFG-Core body temperature (+ tfc-ambiental-refreshed); Cold Sweat would double-handle player temperature
- [28] Block Runner (by Fuzs): **IN TFG** - TFG file: BlockRunner-v8.0.4-1.20.1-Forge.jar
- [29] Lychee (Neo/Forge) (by Snownee): **INCLUDE** - Lychee-1.20.1-Forge-5.2.1.jar (CF 567403/8030949, lychee) requires=-; [optional] Recipe engine, mandatory dependency of Hardrock Tools & Materials.
- [30] Explosive Enhancement: Reforged (by xylonity): **SKIP** - cosmetic/QoL, not needed (Watut + CoroUtil add player status rendering; JamLib/Cupboard/RightClickHarvest/Clean Swing/Explosive Enhancement/Clumps are optional QoL)
- [31] Better Combat [Fabric & Forge] (by daedelus_dev): **SKIP** - changes global combat; crew bodies call Player.attack; needs playerAnimator which has no Forge 1.20.1 build in CurseForge's list
- [32] Kiwi 🥝 (Neo/Forge) (by Snownee): **SKIP** - Kiwi is only an OPTIONAL dependency of Lychee 5.2.1 (read mods.toml); its mixins also hit FastSuite's AuxRecipeManager and GameData (ModernFix)
- [33] Astikor Carts TFC (by Verph): **IN TFG** - TFG file: TFCAstikorCarts-1.20.1-1.1.8.3.jar (Crownfall has 1.1.9; TFG keeps 1.1.8.3. 1.1.9 also resolves against the bundled TFC)
- [34] Drippy Loading Screen (by Keksuccino): **IN TFG** - TFG file: drippyloadingscreen_forge_3.1.0_MC_1.20.1.jar
- [35] Minecolonies: War 'N Taxes  (by mchivelli): **INCLUDE** - WarNTaxes-5.0.9.jar (CF 1129258/8761258, minecolonytax) requires=minecolonies; Wars, taxes, vassals for colonies. CurseForge 5.0.9 (Aug 2026) is newer than Modrinth minecolony-tax-addon 3.2.2.
- [36] Lithium (Fabric/NeoForge) (by JellySquid): **SKIP** - no Forge 1.20.1 build (CurseForge file list: Fabric/NeoForge 1.21.x only); TFG ships radium-reforged as its Lithium port
- [37] [EMF] Entity Model Features [Fabric & Forge] (by Traben): **SKIP** - client renderer/cosmetic; TFG already runs Oculus/Embeddium/ImmediatelyFast/EntityCulling and a render-mod mix is a conflict risk
- [38] JamLib (by jamalam360): **SKIP** - cosmetic/QoL, not needed (Watut + CoroUtil add player status rendering; JamLib/Cupboard/RightClickHarvest/Clean Swing/Explosive Enhancement/Clumps are optional QoL)
- [39] Just Enough Breeding (JEBr) (by Christofmeg): **SKIP** - TFG uses EMI; JEI would duplicate the recipe viewer (JEBr and MezzConfig exist only for JEI)
- [40] AllTheLeaks (Memory Leak Fix) (by Uncandango): **IN TFG** - TFG file: alltheleaks-1.1.4+1.20.1-forge.jar
- [41] Rhino (by Lat): **IN TFG** - TFG file: rhino-forge-2001.2.3-build.10.jar
- [42] Jade 🔍 (by Snownee): **IN TFG** - TFG file: Jade-1.20.1-Forge-11.13.3.jar
- [43] I ❤ TFC (I Heart TFC) (by alekiponi): **IN TFG** - TFG file: ihearttfc-1.20.1-1.0.2.jar
- [44] CoroUtil (by Corosus): **SKIP** - cosmetic/QoL, not needed (Watut + CoroUtil add player status rendering; JamLib/Cupboard/RightClickHarvest/Clean Swing/Explosive Enhancement/Clumps are optional QoL)
- [45] Roads and Roofs TFC (by Therighton): **IN TFG** - TFG file: rnr-0.2.6-1.20.1.jar
- [46] TFC Vessel Tooltip (by HermitOwO): **IN TFG** - TFG file: TFCVesselTooltip-1.20.1-1.1.jar
- [47] Caravans & Convoys - Automatic Trade (by Barunn): **INCLUDE** - caravansconvoys-forge-1.0.14-1.20.1-java17.jar (CF 1599431/9294591, caravansconvoys) requires=-; Docks + horse-drawn wagon trade routes.
- [48] AstikorCarts Redux (by jusipat): **IN TFG** - TFG file: astikorcarts-1.20.1-1.1.8.jar
- [49] Starter Kit (by Serilum): **SKIP** - Starter Kit gives items on first login; crew fake players log in as new players. Collective is only its library
- [50] Spindles TFC (by sir_Robson): **INCLUDE** - TFC_Spindles-1.20.1-forge-1.0.1.jar (CF 1258816/6749542, tfc_spindles) requires=tfc_items; [optional] Spinning for TFC.
- [51] TFCGenViewer (by NotEnoughMail): **IN TFG** - TFG file: tfcgenviewer-1.20.1-1.5.1.jar
- [52] SDM Shop [Forge/Fabric] (Legacy) (by Sixik): **INCLUDE** - SDMShop-forge-1.20.1-7.2.2.jar (CF 948942/7935087, sdmshop) requires=architectury,sdm_ui_lib,ftblibrary,sdmeconomy; Shop GUI/economy front end.
- [53] FTB Ranks (NeoForge) (by FTB): **IN TFG** - TFG file: ftb-ranks-forge-2001.1.7.jar
- [54] TFC Ore Washing (by sir_Robson): **INCLUDE** - tfc-ore-washing-1.20.1-forge-1.0.6.jar (CF 959262/6145630, tfcorewashing) requires=tfc; [optional] Ore washing for TFC.
- [55] What Are They Up To (Watut) (by Corosus): **SKIP** - cosmetic/QoL, not needed (Watut + CoroUtil add player status rendering; JamLib/Cupboard/RightClickHarvest/Clean Swing/Explosive Enhancement/Clumps are optional QoL)
- [56] TownTalk (by Raycoms): **INCLUDE** - towntalk-1.20.1-1.1.0.jar (CF 900364/5355511, towntalk) requires=-; Citizen voice lines (49 MB).
- [57] spark (by Iucko): **INCLUDE** - spark-1.10.53-forge.jar (CF 361579/4738952, spark) requires=-; Server profiler for lag diagnosis.
- [58] Just Enough Items (JEI) (by mezz): **SKIP** - TFG uses EMI; JEI would duplicate the recipe viewer (JEBr and MezzConfig exist only for JEI)
- [59] BlockUI (by Raycoms): **INCLUDE** - blockui-1.20.1-1.0.193.jar (CF 522992/7541343, blockui) requires=-; MineColonies/Structurize GUI library (MineColonies needs >=1.0.190-snapshot).
- [60] Entity View Distance [Unofficial NeoForge] (by LostPattern): **SKIP** - NeoForge-only: CurseForge file list has only 1.21.x NeoForge files, no Forge 1.20.1 build
- [61] Simple Discord Link Bot (by HypherionSA): **SKIP** - needs an external Discord bot token/config; crew already posts to Discord by webhook. CraterLib is only its library
- [62] TFC Textile (by oatobaazul): **SKIP** - overlaps TFG-Core body temperature (+ tfc-ambiental-refreshed); Cold Sweat would double-handle player temperature
- [63] TFC Support Indicator (by floweynt): **IN TFG** - TFG file: tfc_support_indicator-1.0.7+mc1.20.1.jar
- [64] CraterLib (by HypherionSA): **SKIP** - needs an external Discord bot token/config; crew already posts to Discord by webhook. CraterLib is only its library
- [65] FramedBlocks (by XFactHD): **IN TFG** - TFG file: FramedBlocks-9.4.3.jar
- [66] Structurize (by Raycoms): **INCLUDE** - structurize-1.20.1-1.0.818.jar (CF 298744/8610456, structurize) requires=blockui,domum_ornamentum; MineColonies blueprint/placement library; MineColonies 1301 needs >=1.0.818.
- [67] Curios API (by TheIllusiveC4): **IN TFG** - TFG file: curios-forge-5.14.1+1.20.1.jar
- [68] Clean Swing Through Grass (by Raycoms): **SKIP** - cosmetic/QoL, not needed (Watut + CoroUtil add player status rendering; JamLib/Cupboard/RightClickHarvest/Clean Swing/Explosive Enhancement/Clumps are optional QoL)
- [69] Farmer's Delight (by vectorwing): **INCLUDE** - FarmersDelight-1.20.1-1.3.4.jar (CF 398521/8765179, farmersdelight) requires=-; [optional] Cooking/farming; required by Farmers TFC.
- [70] Palette Swap for MineColonies (by DarkAges): **INCLUDE** - structurizereplacements-1.20.1-0.4.67.jar (CF 1567948/8353116, structurizereplacements) requires=structurize; Re-palette blueprints per block.
- [71] SDM UI Lib [Forge/Fabric] (by Sixik): **INCLUDE** - sdm_ui_lib-forge-1.20.1-1.8.3.jar (CF 1095061/6086204, sdm_ui_lib) requires=-; UI library for SDM Shop (needs >=1.20.1-1.8.3).
- [72] New Animals for TerraFirmaCraft (by BlackAuresArt): **IN TFG** - TFG file: TerraFirmaCraft_New_Animals.zip (resource pack)
- [73] KubeJS (by Lat): **IN TFG** - TFG file: kubejs-forge-2001.6.5-build.24.jar
- [74] GeckoLib (by Gecko): **IN TFG** - TFG file: geckolib-forge-1.20.1-4.8.4.jar
- [75] Corpse (by henkelmax): **IN TFG** - TFG file: corpse-forge-1.20.1-1.0.23.jar
- [76] Konkrete (by Keksuccino): **IN TFG** - TFG file: konkrete_forge_1.8.0_MC_1.20-1.20.1.jar
- [77] Drippy Early Loading Module (by Keksuccino): **SKIP** - NeoForge-only: CurseForge file list has only 1.21.x NeoForge files, no Forge 1.20.1 build
- [78] Farmers TFC (by Vvxzv): **INCLUDE** - farmerstfc-2.1.7-1.20.1.jar (CF 1318733/8700140, farmerstfc) requires=tfc,farmersdelight; [optional] Farmer's Delight x TFC integration (TFC API check OK vs bundled 3.2.28).
- [79] Cupboard (by someaddon): **SKIP** - cosmetic/QoL, not needed (Watut + CoroUtil add player status rendering; JamLib/Cupboard/RightClickHarvest/Clean Swing/Explosive Enhancement/Clumps are optional QoL)
- [80] Configurable (by bawnorton): **SKIP** - NeoForge-only: CurseForge file list has only 1.21.x NeoForge files, no Forge 1.20.1 build
- [81] playerAnimator (by KosmX): **SKIP** - changes global combat; crew bodies call Player.attack; needs playerAnimator which has no Forge 1.20.1 build in CurseForge's list
- [82] MineColonies: War 'n Nobility (by Barunn): **INCLUDE** - warnnobility-forge-1.1.4-1.20.1-java17.jar (CF 1580789/9294588, warnnobility) requires=minecolonies,minecolonytax; Feudal ranks/counties on top of War 'N Taxes.
- [83] FerriteCore ((Neo)Forge) (by malte0811): **IN TFG** - TFG file: ferritecore-6.0.1-forge.jar
- [84] TFC More Items (by sir_Robson): **INCLUDE** - tfc_items-1.20.1-forge-1.1.1.jar (CF 1189837/6304834, tfc_items) requires=-; [optional] Extra TFC items; required by Spindles TFC.
- [85] FTB Quests (NeoForge) (by FTB): **IN TFG** - TFG file: ftb-quests-forge-2001.4.22.jar
- [86] Epic Knights: Shields, Armor and Weapons [Fabric/Forge/NeoForge] (by magistu_): **INCLUDE** - epic-knights-1.20.1-forge-10.15.jar (CF 509041/8931670, magistuarmory) requires=architectury,cloth_config; Medieval armour/weapons.
- [87] Patchouli (by Vazkii): **IN TFG** - TFG file: Patchouli-1.20.1-85-FORGE.jar
- [88] Better With Minecolonies (by Kreezxil): **SKIP** - Better With MineColonies is a 2023 build (1.20), stale against MineColonies 1.1.1301
- [89] TFPRevivedCompat (by Mr101Freaking): **SKIP** - NeoForge-only: CurseForge file list has only 1.21.x NeoForge files, no Forge 1.20.1 build
- [90] TFC Aged Alcohol (by HermitOwO): **IN TFG** - TFG file: TFCAgedAlcohol-1.20.1-2.3.jar
- [91] TFC Ore Marker: Expanded (by Quizer9O8): **SKIP** - resource pack / shader, not a mod (no 1.20.1 build or not needed; TFG ships its own resource packs)
- [92] NeoOrigins (by CyberDay): **SKIP** - NeoForge-only: CurseForge file list has only 1.21.x NeoForge files, no Forge 1.20.1 build
- [93] JourneyMap (by techbrew): **SKIP** - TFG ships Xaero's minimap/world map; no 1.20.1 build of the TFC integration
- [94] Architectury API (by shedaniel): **IN TFG** - TFG file: architectury-9.2.14-forge.jar
- [95] FancyMenu (by Keksuccino): **IN TFG** - TFG file: fancymenu_forge_3.8.1_MC_1.20.1.jar
- [96] Clumps (by Jaredlll08): **SKIP** - cosmetic/QoL, not needed (Watut + CoroUtil add player status rendering; JamLib/Cupboard/RightClickHarvest/Clean Swing/Explosive Enhancement/Clumps are optional QoL)
- [97] KubeJS TFC (by NotEnoughMail): **IN TFG** - TFG file: kubejs_tfc-1.20.1-1.3.5.jar
- [98] Animals Trap for TFC (by sir_Robson): **INCLUDE** - AnimalTrapTFC-1.20.1-forge-1.0.1.jar (CF 954871/4997031, animaltraptfc) requires=animaltrap,tfc; [optional] TFC animals for the traps (beta, Dec 2023).
- [99] TerraFirmaCraft (by Dries007): **IN TFG** - TFG file: bundled inside TerraFirmaGreg-Core 0.9.31 (tfc 3.2.28)
- [100] Cloth Config API (Fabric/Forge/NeoForge) (by shedaniel): **IN TFG** - TFG file: cloth-config-11.1.136-forge.jar
- [101] Melody (by Keksuccino): **IN TFG** - TFG file: melody_forge_1.0.3_MC_1.20.1-1.20.4.jar
- [102] Multi-Piston (by Raycoms): **INCLUDE** - multipiston-1.20-1.2.43-RELEASE.jar (CF 303278/5204918, multipiston) requires=blockui,structurize; Multi-directional piston block (MineColonies team). RELEASE 1.2.43 chosen; the 2025 snapshot 0.0.47 also resolves against Structurize/BlockUI.
- [103] Embeddium (by FiniteReality): **IN TFG** - TFG file: embeddium-0.3.31+mc1.20.1.jar
- [104] TFC-MineCol-Compat (by Mr101Freaking): **SKIP** - NeoForge-only: CurseForge file list has only 1.21.x NeoForge files, no Forge 1.20.1 build
- [105] MineColonies (by Raycoms): **INCLUDE** - minecolonies-1.20.1-1.1.1301.jar (CF 245506/9058213, minecolonies) requires=structurize,blockui,domum_ornamentum; Colonies, citizens, builders: the base of starbases/colonies. Newest non-snapshot 1.20.1 release (Oct 4 2026).
- [106] Neruina - Ticking Entity Fixer (by bawnorton): **INCLUDE** - neruina-3.3.5+1.20.1-forge.jar (CF 851046/9220570, neruina) requires=-; [optional] Catches ticking-entity exceptions instead of crashing (beta).
- [107] UniLib (by CDAGaming_): **IN TFG** - TFG file: UniLib-1.2.1+1.20.1-forge.jar
- [108] Carry On (by Tschipp): **IN TFG** - TFG file: carryon-forge-1.20.1-2.1.2.7.jar
- [109] Epic Knights: Addon (by magistu_): **INCLUDE** - epic-knights-addon-1.20.x-forge-2.6.jar (CF 925866/7667762, magistuarmoryaddon) requires=magistuarmory; Epic Knights addon (needs Epic Knights >=10.8).
- [110] FTB Teams (NeoForge) (by FTB): **IN TFG** - TFG file: ftb-teams-forge-2001.3.2.jar
- [111] MakeUp - Ultra Fast | Shaders (by XavierFST): **SKIP** - client renderer/cosmetic; TFG already runs Oculus/Embeddium/ImmediatelyFast/EntityCulling and a render-mod mix is a conflict risk
- [112] TFCDraughtworks (by z1z1y2): **SKIP** - NeoForge-only: CurseForge file list has only 1.21.x NeoForge files, no Forge 1.20.1 build
- [113] NeOculus (by kaguya154): **SKIP** - client renderer/cosmetic; TFG already runs Oculus/Embeddium/ImmediatelyFast/EntityCulling and a render-mod mix is a conflict risk
- [114] FTB Library (NeoForge) (by FTB): **IN TFG** - TFG file: ftb-library-forge-2001.2.13.jar
- [115] TFC Registry API (by Verph): **SKIP** - NeoForge-only: CurseForge file list has only 1.21.x NeoForge files, no Forge 1.20.1 build
- [116] Wary Predators for TFC (by CorvusIncognitus): **SKIP** - NeoForge-only: CurseForge file list has only 1.21.x NeoForge files, no Forge 1.20.1 build
- [117] [ETF] Entity Texture Features - [Fabric & Forge] (by Traben): **SKIP** - client renderer/cosmetic; TFG already runs Oculus/Embeddium/ImmediatelyFast/EntityCulling and a render-mod mix is a conflict risk
- [118] Compatibility addon for MineColonies (by gisellevonbingen): **INCLUDE** - MineColonies_Compatibility-1.20.1-2.142.jar (CF 1006214/9254868, minecolonies_compatibility) requires=minecolonies,minecolonies_tweaks; MineColonies compat with other mods (Butchercraft etc.).
- [119] Butchercraft (by Lance5057): **INCLUDE** - butchercraft-2.4.1.jar (CF 265715/6058842, butchercraft) requires=-; Semi-realistic butchering (standalone; Survivor's Butchery integration skipped, see AUDIT).
- [120] SDM  Economy [Forge/Fabric] (by Sixik): **INCLUDE** - SDMEconomy-1.20.1-forge-2.2.0.jar (CF 1102542/6689080, sdmeconomy) requires=architectury; Currency ledger library (SDM Shop 7.2.2 needs >=2.2.0).
- [121] CraftPresence (by CDAGaming_): **IN TFG** - TFG file: CraftPresence-2.7.1+1.20.1-forge.jar
- [122] RightClickHarvest (by jamalam360): **SKIP** - cosmetic/QoL, not needed (Watut + CoroUtil add player status rendering; JamLib/Cupboard/RightClickHarvest/Clean Swing/Explosive Enhancement/Clumps are optional QoL)
- [123] JourneyMap TFC Integration (by Coin0804): **SKIP** - TFG ships Xaero's minimap/world map; no 1.20.1 build of the TFC integration
- [124] Sophisticated Core (by P3pp3rF1y): **IN TFG** - TFG file: sophisticatedcore-1.20.1-1.5.16.2433.jar
- [125] Mouse Tweaks (by YaLTeR): **IN TFG** - TFG file: MouseTweaks-forge-mc1.20.1-2.25.1.jar
- [126] Barrels 2012 (by EERussianguy): **IN TFG** - TFG file: barrels_2012-2.1.jar
- [127] Collective (by Serilum): **SKIP** - Starter Kit gives items on first login; crew fake players log in as new players. Collective is only its library

## TFC API check (bundled TFC 3.2.28 in TerraFirmaGreg-Core 0.9.31)
- Farmers TFC 2.1.7: 112 TFC member refs, 98 resolved, 14 inherited-from-outside, 0 missing. Mixins hit TFCCakeBlock + FirmaLife FLBeehiveBlockEntity (no TFG mixin on them).
- TFC Astikor Carts 1.1.9 (not taken, TFG has 1.1.8.3): 0 missing. Survivor's Abilities 1.5.1: 0 missing (skipped for mixin overlap, below).
- Butchercraft, Hardrock Tools (htm), TFC More Items, Spindles TFC, TFC Ore Washing, Animals Trap for TFC: no net/dries007/tfc reference in any class (data driven). Their recipes/tags
  reference TFC ids that only a boot can validate.
## MineColonies API check (MineColonies 1.1.1301, Structurize 1.0.818, BlockUI 1.0.193)
- Mixin target classes: Tweaks 2.107 (48), Compatibility 2.142 (23 present), War 'n Nobility (WarSystem of War 'N Taxes), Palette Swap (8 Structurize classes), Survivor's Butchery: all exist.
- Handler method names checked against the target classes: Tweaks 101 refs, Compatibility 51, 0 real misses (5 names are vanilla-inherited methods like `hurt`, which the production jar carries as SRG names behind the refmap).
- Member-reference (api_check) runs: Multi-Piston (both versions) vs Structurize+BlockUI, Palette Swap vs Structurize, War 'n Nobility vs MineColonies, TownTalk: 0 missing. The same run for Tweaks/Compatibility
  was too slow in the checker (regex on a 78 MB jar) and was replaced by the method-name check above.
- Version ranges: MineColonies 1301 needs structurize >=1.20.1-1.0.818, blockui >=1.20.1-1.0.190-snapshot, domum_ornamentum >=1.20.1-1.0.288-snapshot (TFG ships 1.0.304-snapshot); Tweaks needs
  minecolonies >=1.1.1197; Compatibility needs minecolonies >=1.1.1275 AND Tweaks >=2.107; War 'N Taxes >=1.1.1237; War 'n Nobility needs War 'N Taxes.

## Mixin overlap with TFG (class level; same class patched by an included mod and a TFG mod)
- Hundred Years Warfare (64 mixins, `required: true`, config plugin): ChunkMap (3 mixins + accessor + TrackedEntity freecam x2) overlaps TFG-Core, ModernFix, Radium, FTB Chunks, KubeJS, AE2, Tumbleweed, Lithostitched, AllTheLeaks;
  ServerPlayer (ServerPlayerChunkVisibilityMixin) overlaps ModernFix, PlayerRevive, TACZ, Immersive*, Exposure; ServerLevel x3, EntitySectionStorage, FloatGoal, Mob, LivingEntity, Entity;
  TACZ classes (LivingEntityAmmoCheck, ModernKineticGunScriptAPI, EntityUtil) which TFG ships (timeless-and-classics-zero 1.1.8-hotfix2); targets of Epic Fight / Iron's Spellbooks / GunDB are absent.
- Neruina 3.3.5: MinecraftServer, ServerLevel, ServerGamePacketListenerImpl, PlayerList, Entity (overlaps ModernFix, Saturn, Packet Fixer, NoChatReports, KubeJS, Create threaded trains).
- SDM Shop: FTB Library BaseScreen/Widget/Panel (client GUI) - AllTheLeaks also patches BaseScreen.
- Lychee: ChunkMap, Entity. Small Ships: Entity, LivingEntity. All other included mods patch only their own classes or nothing in TFG's set.
- No TFG mod patches MineColonies/Structurize/BlockUI, and none of the included addons patch TFC except Farmers TFC (TFCCakeBlock, FLBeehiveBlockEntity; no TFG mixin on those two).
- Survivor's Abilities (SKIPPED) mixes TFCFoodData.tick (TAIL + INVOKE), ForgeEventHandler.onPlayerTick overburdened check and NutritionData; TFG-Core mixes the same methods
  (TFCFoodDataMixin tick TAIL, TFCFoodDataNutrientEffectsMixin tick INVOKE + addExhaustion + heal redirect, NutritionDataMixin, ForgeEventHandlerMixin WrapOperation). Not safe without a boot test, and Survivor's Butchery hard-requires it.

## Coins / currency
- TFG coins: GT forming press (nugget + cylinder casting mold) AND Create pressing (nugget -> coin: copper/wrought iron/steel/gold/brass/zinc/blue steel), createdeco coins (lead's note).
- SDM Economy is a LEDGER currency (Crownfall config/SDMEconomy/currencies/currencies.data: id `sdmcoin`, symbol, default value), no item needed.
- War 'N Taxes pays taxes into that ledger (`SDMCurrencyName = "sdmcoin"`) and has `CurrencyItemName = "minecraft:emerald"` (default) for an item form: set it to a TFG coin item id or keep ledger-only.
  War 'n Nobility `buyin_item` was minecraft:structure_void in Crownfall (rank cannot be bought).
- Crownfall made its own coin items by KubeJS (kubejs:penny/mark/noble, startup script crownfall_coins.js) and re-pointed vanilla iron/gold recipe inputs of caravansconvoys, warnnobility and
  hundred_years_war to `#c:ingots/wrought_iron` / `#c:ingots/gold` (kubejs/server_scripts/crownfall_economy.js). TFG has the same problem (no vanilla iron), so those recipes need a KubeJS patch.

## RISKS for the boot test (in order)
1. **Hundred Years Warfare**: 12.8 MB, `required` mixins on ChunkMap/TrackedEntity/ServerPlayer/ServerLevel. Expect conflicts with ModernFix/Radium (chunk map), the crew fake players (ServerPlayerChunkVisibilityMixin, freecam tracker), and
   TACZ mixins applied to TFG's TACZ. If the boot or TPS breaks, drop it first (nothing else requires it; mod id `hundred_years_war`).
2. **MineColonies 1.1.1301 + Domum Ornamentum 1.0.304 (TFG's)**: version ranges satisfied; MineColonies is 78 MB and the crew mod's colony hooks are untested against it. TFC rules (no vanilla iron/gold/glass) break many MineColonies/Structurize
   recipes: Crownfall fixed them in kubejs/server_scripts/crownfall_minecolonies_tfc.js (barrel_block, rack, build_goggles, spear, quarry, caliper, sceptersteel, architectscutter...); needs a port to TFG's KubeJS.
3. **MineColonies Tweaks 2.107 + Compatibility 2.142** are betas built for MineColonies ~1.1.1275-1.1.13xx; checked by class and method name only.
4. **Lychee (+HTM, Animals Trap)**: recipe engine with ChunkMap/Entity mixins next to TFG's FastSuite/KubeJS recipe pipeline; optional chain, drop Lychee, htm, animaltrap, animaltraptfc together.
5. **Farmer's Delight + Farmers TFC**: FD adds non-TFC food items (no TFC decay/nutrition unless Farmers TFC patches them) next to TFG-Core's nutrient/contaminant system and KubeJS food scripts; TFG KubeJS may not know the items.
6. **Neruina** swallows ticking-entity exceptions (interacts with the crew mod's tick guard and FullStack Watchdog) - it is a beta; check it does not hide real crashes.
7. Recipes of caravansconvoys / warnnobility / hundred_years_war use vanilla iron/gold/emerald (see Coins).
8. Size: TownTalk is 49 MB, MineColonies 78 MB, HYW 12.8 MB (client zip grows ~150 MB).
9. SDM Shop's FTB Library GUI mixins vs AllTheLeaks (client only).
10. Butchercraft without Survivor's Butchery: no TFC animal integration (skipped, see above); MineColonies Compatibility adds Butchercraft mixins (ButcherBlockBlockEntity, MeatHookBlockEntity) - targets exist in 2.4.1.
11. Lock caveat: TFC Astikor Carts 1.1.8.3 (TFG) stays; Crownfall's 1.1.9 would also resolve but is not needed.

## Not verified
- Nothing here has been booted. Hundred Years Warfare / MineColonies behaviour with the crew's fake players is unknown.
- Data-driven TFC addons (recipes/tags/loot) only fail at world load.
- cfwidget is a third-party mirror of CurseForge; file ids/names came from it and each jar was then re-downloaded from forgecdn and hashed, so the lock itself does not depend on cfwidget.
- CurseForge project pages were not scraped for "Server/Client" environment flags: side is `both` for every entry (all add registries/gameplay); no jar sets displayTest, and the dependency `side` values in their mods.toml are all BOTH except one CLIENT-side dependency entry each in Structurize and War 'n Nobility.
