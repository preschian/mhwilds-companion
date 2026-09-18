# Datamine notes (MH Wilds)

How the companion dataset in `data/monsters.json` + `data/icons/` was built
from the game install, and what was learned about the formats. All values
below come from the installed game + patches (merged newest-wins).

## Sources

| Data | Game file(s) |
|------|--------------|
| Hitzones per part/state | `GameDesign/Enemy/EmXXXX/VV/Data/*_Param_Parts.user.3` |
| Monster names (+Frenzy/Arch-tempered) | `GameDesign/Text/Excel_Data/EnemyText.msg.23` |
| Part names | `GameDesign/Text/Excel_Data/EnemyPartsTypeName.msg.23` |
| Species/attributes | `EnemySpeciesName.msg.23`, `EnemyReport*.msg.23` |
| Icons (512px BC7) | `GUI/ui_texture/tex000000/tex_EmIcon_*/tex_EmIcon_EM*.tex.*` |
| Item glyphs (white) | `GUI/ui_texture/tex000000/tex000201_0_IMLM4.tex.*` (100px grid, 20 cols) |
| Item badges (color) | `.../tex000201_20_IMLM4.tex.*` (64px grid, 8 cols) |
| Badge table | `GameDesign/GUI/Common/_UserData/AddIconData.user.3` |
| Tint palette | `GUI/colorPreset.gcp.2` (`GCPR`: count + 40B entries, 4×ABGR) + `app.ColorPreset.TYPE` enum |
| Struct database | `il2cpp_dump.json` (REFramework SDK dump, beside the exe) |
| Ecology/tips/features | `EnemyText.msg.23` (`EnemyText_EXP/FEATURES/TIPS/MEMO/FIRST_CAPTURE/BOSS_EXP_EM*`) |
| Species/serials/text links | `GameDesign/Common/Enemy/EnemyData.user.3` (149 rows; `_enemyId` = `ID_Fixed`, `_Species` 1–21) |
| Habitat/reco/SP attacks | `EnemyReportBossData` (34) / `EnemyReportZakoData` (19) / `EnemyReportAnimalData` (70) |
| SP/attribute/break names | `EnemyReportSpecialAttackTypeText/WeaponAttributeText/PartsBreakTypeName.msg.23` |
| Part break display | `EnemyReportAnatomyPartsBreakData` (10 diagram slots → partsType + break type) |
| Hunter titles | `EnemyReportBossTitleData` (Hunt 20/30/40/50 → `Title_Word`) |
| Size/crowns | `Enemy/CommonData/Data/EmCommonRandomSize.user.3` (scale/prob tables + per-enemy rank bounds) |
| Tempered/enrage/stamina/ride | `GameDesign/Enemy/EmXXXX/VV/Data/*_Param_Legendary/Angry/Stamina/Ride/Basic.user.3` |
| Quests/locales | `GameDesign/Mission/Mission*/*MsData` + `BossZakoLayout_*` + `_Quest/*_QuestData` |
| Quest titles/texts | `GameDesign/Text/Mission/Mission*.msg.23` + `Mission_Quest*` templates |

PAKs: gameplay data in `re_chunk_000.pak` + `patch_001..015`; textures in
`re_chunk_000.pak.sub_000.pak` + its patches. File list `MHWs.list`
(dtlnor/MonsterHunterWildsModding) + REToolCustom (FluffyQuack fork with
Wilds TEX/GDeflate support) for extract, texconv (DirectXTex) for DDS→PNG.

## Format findings

- `.user` = `USR\0` header + RSZ v16 payload (`RSZ\0` at 0x30). Instance
  table entries are 8 bytes: type hash + crc. Entry points are 1-based and
  the null instance 0 carries no bytes.
- **RSZ type hash = murmur3-32 (seed `0xFFFFFFFF`) of the il2cpp class
  name.** Verified against 323k dump names; resolves every instance.
- il2cpp_dump classes carry an `RSZ` array (align/size/code/offset per
  field) — a complete serialization schema, no REFramework dump needed.
- **Array counts and single Object refs align to 4**, not the native
  pointer align 8 (matches re-editor's `GetAlign()`, proven on
  `cMultiParts._PriorityConditions`). Guid-array elements align per element.
- `.msg` v23 (`GMSG`): XOR stream cipher (16-byte key, chained) over the
  data section; entries carry guid/crc/hash + per-language UTF-16 offsets.
  See `re-editor/Common/Models/MSG.cs` for the reference reader.
- `.rcol` (`RCOL`) embeds an RSZ section; `Shell_*` files are projectile
  data (gunlance-style shells), **not** hitzones.

## Hitzone model (`EmParamParts`)

- `cMeat` = Guid + 10×S32: Slash/Blow/Shot/Fire/Water/Thunder/Ice/Dragon/
  Stun/LightPlant, 56 bytes each.
- `cParts` = Guid + Vital[] + RodExtract (kinsect) + 6 meat Guids
  (Normal/Break/Custom1-5) + PartsType + flag. Field order is the RSZ array
  order (proven by Guid cross-reference), not offset order.
- `cWeakPoint` / `cScarPoint` carry their own meat Guid + link-part Guid.
- `PARTS_TYPE` values are stable S32 ids (e.g. Head `-212024896`, Tail
  `2000370944`); display names come from `EnemyPartsTypeName.msg`
  (`m…` prefix = negative).
- `Em0160_50` (Guardian Arkveld) has **no** Param_Parts file: it shares
  `Em0160_00`. `Em1062` is a debug dummy (HP 999999, no name/icon).
  `EM0000` is the `?` placeholder icon.

## Validation

Cross-checked against independent Kiranico-derived data
(sockbats/MH-Wilds-Monster-Database): **2727/2745 normal-state cells
(99.3%) match**. Deltas, all kept as file truth in the dataset:

- Kinsect extract differs on a few parts (Rathalos/Rathian legs
  ORANGE vs WHITE, Rathalos neck/wings, Gore Magala wings).
- Zoh Shia base values are uniformly lower than Kiranico's (balance patch
  drift); Kiranico's `(Darkened)` rows correspond to custom-state slots.
- Wound-effective numbers (Kiranico `wounded_hitzones`) are computed, not
  stored; the dataset ships the raw scar/weakpoint meats instead.

Our data additionally covers monsters missing from that source: Lagiacrus,
Seregios, Gogmazios, Omega Planetes/Micros.

## Rewards model (`EnemyRewardData`)

Per-monster tables in `GameDesign/Common/Enemy/EMXXXX_*.user.3`, one
`cData` entry per lottery line: story slot (low rank: item/count/rate) +
ex arrays (high rank). dataId hundreds digit = category, verified against
community tables (Rathian oracle: 21/21 match):

| dataId | Category | Notes |
|--------|----------|-------|
| 100s | Body carve | One lottery (lines sum 100); carve count in `Param_Hagitori` (`Nullable<Int32>` = flag + value; null = game default) |
| 200s | Tail carve | RW016 head; small-monster 200s with other heads are drops |
| 300s | Part break | Per-part when partsIndex ≥ 0 (= `RewardTableIndex` in the monster's `Param_PartsBreakReward`); one shared pool when -1 |
| 400s | Wound destroy | One lottery |
| 500s | Target rewards | One table per roll (8 rolls); ex[0] is the primary, rest kept as `alts` |
| 110/120/150/210s | Field drops | Inferred: shiny/pickup lots (contents exact, trigger unverified) |
| 600s | Bonus | Wyverian bloodstones |
| 800/900s | Gather | Endemic life (fish/insects) |

`PARTS_TYPE` and break linkage reuse the hitzone maps. Item catalog
(`data/materials.json`, 782 items: id/name/rarity/prices + English `desc`)
comes from `Common/Item/itemData.user.3` + `Item.msg.23`
(`Item_IT_<id>` names, `Item_IT_EXP_<id>` explains; 652/782 — every named
item covered, the rest are unreleased `ITEM<…>` placeholders).

### Item catalog field values

`type` is `app.ItemDef.TYPE`: 0 EXPENDABLE (consumables: Potion, Honey),
1 TOOL (reusables: Whetstone, Capture Net), 2 MATERIAL (crafting parts:
507 items), 3 SHELL (bowgun ammo), 4 BOTTLE (bow coatings),
5 POINT (village exchange items), 6 GEM (decoration orbs).

`rarity` (`_Rare`) spans 11–18, **lower is rarer**: Potion 18, Mega 17,
Max 16, Ancient 14, Rathian Scale+ 13, Rathian Ruby 12. Suspected
in-game display is R1–R8 via `19 − value` (unverified: the display
mapping lives in game code, not data).

`icon.badge`/`icon.badgePos`: corner overlay marker (89/782 items have
one; rest `null`). `LT`/`RT` = left/right-top corner. The 5 used badges
(`AddIcon` → glyph): `SHELL_LV1` → star = upgraded consumables
(Mega/Ancient) + Valuable Material; `WISH_ITEM` → pouch = trade-ins
(aloe, treasures); `LOCK` → padlock = village cooking ingredients;
`FOR_ARMOR` → gauntlet = Sword orbs; `EQUIP_TEMPERED` → plus = Armor
orbs. Full render = glyph × tint + badge at its corner.

## Item icon model

Each item in `itemData.user.3` carries `_IconType` (77 used values),
`_IconColor` (22 used: `I_NONE`..`I_DPURPLE`), `_AddIconType` (5 used) and
`_EquipIcon` (artian shards only; smithy-side). The game renders
base glyph × tint + corner badge:

- Base glyph: atlas cell `max(0, IconType - 1)`, row-major. Verified
  glyph-by-glyph against item names (~70/77: honeycomb, potion flask,
  barrels, traps, ores, ammo...). Full-color cells (icons 92-97,
  unreleased items) pair with `I_NONE` (no tint), confirming the rule.
  `cell = icon` is ruled out: icon 5 is unused while cell 5 is the
  mushroom, so icons 6+ must sit one cell left.
- Tint: `ColorPreset.TYPE` value indexes `colorPreset.gcp.2` directly
  (entry colors match the enum names: `I_GREEN` = green...). All item
  colors have identical 4 slots; slot 0 ships in `data/item_palette.json`.
- Badge: `AddIconData` maps AddIcon → corner (`LT/RT/LB/RB`) + sequence 0
  + pattern. Patterns index the `tex000201_20` sheet, overwhelmingly
  pattern+1; the 5 item-used badges are pinned by semantic match:
  `SHELL_LV1` (Mega/Ancient, LT) → star, `WISH_ITEM` (trade-ins, RT) →
  pouch, `LOCK` (village ingredients, RT) → padlock, `FOR_ARMOR` (orbs,
  RT) → gauntlet, `EQUIP_TEMPERED` (orbs, RT) → plus. `.gui`/`.mov`
  reference textures by hash (no path strings), so the exact pattern
  rects are unverifiable short of a GUI format parser; the three
  non-padlock/gauntlet picks are flagged best-effort.
- `data/materials.json` gains per-item `icon: {glyph, tint, badge,
  badgePos}`; glyphs/badges ship as 82 PNGs under `data/icons/items/`
  (624 KB, tight alpha-bbox crops).

Bonus found while surveying (not extracted): `tex000201_1` holds map
icons + full-color monster minimap icons + white weapon/armor glyphs;
`tex000201_2` holds ailment/buff icons + full-color endemic-life icons.

## Field Guide model (`EnemyReport*`)

- Habitat is a stage bitset: bit 1 Windward Plains, 2 Scarlet Forest,
  3 Oilwell Basin, 4 Iceshard Cliffs, 5 Ruins of Wyveria. Cross-checked
  against all 291 quests' stage/tag fields (story monsters anchor each
  locale: Balahara/Plains, Uth Duna/Forest, Rompopolo/Basin,
  Hirabami/Cliffs, Xu Wu/Ruins).
- `RecoAttributeBit` bit N = `WeaponDef.ATTR` N (1 Fire … 9 Blast).
- `EnemySPAttackBit` bit N = `EnemyReportSpecialAttackTypeData` type N
  (1-based: 1 Weak Roar … 34 HP Penalty), verified per monster
  (Gore Magala bit 25 = Frenzy, Seregios bit 24 = Bleeding, Mizutsune
  bits 30/31 = Bubbleblights).
- Star cutoffs: physical hitzone [1,20,40,60,80], element
  [1,15,20,30,80], shiny drops [15,30,45,60,75].
- Break display types: Weak Point / Breakable (×2/×5) / Severable
  (×4/×6) / combos; merged onto `partsBreak[].breakType` (163/172).
- Titles: 4 unlocks per boss (Hunt 20/30/40/50 → title words);
  Zoh Shia has 8 rows.

## Quest model (`data/quests.json`, 291)

- Locale resolution: `MsData._BeaconSetStage` → emset tag → QuestData
  stage; `1044114240` = hub/departure (not a locale). Special venues:
  1181994624 Arena, 544388992 Special Arena, 2009549184 Wounded Hollow,
  13836 Gogmazios siege (Basin), -1869346688 Grand Hub.
- QuestData (`_Quest/`) exists only for 33 HR/event/arena quests;
  optionals carry no params. Quest types: 0 HUNTING, 1 KILL, 2 CAPTURE,
  4 TRANSPORT, 5 ARENA, 6 BOSSRUSH; QuestData `_EmTargetID` 101–105 are
  layout slots, not EmIDs — monster links come from BossZako mains.
- Titles: real `Mission*_000` text when present (story/side/investigation
  quests); else templated (`Hunt/Slay/Capture the X`, `X Investigation`,
  `Hunt all target monsters`) with `titleGuessed: true`. Optional star =
  3rd mission digit (verified: 105013→lv5, 106007→lv6); LR ≤3★, HR ≥4★.
- Wild habitat (guide table) vs quest venue are independent: 4 quests
  legitimately fall outside habitat — 730015 (Nerscylla *invades* the
  Plains), 199004/199012 (cross-locale events), 005390 (Zoh Shia
  scripted finale).

## Size + per-monster params

- `sizeClass` = `MODEL_SIZE` (S/M/L/LL…); `sizeTables` = per-variant
  reward-rank bounds (`EM_REWARD_RANK_01..10`) + scale/prob distribution
  (scales ~88–125, prob weights).
- `tempered` = normal/king/hard tiers (`Param_Legendary` suffix groups):
  motion/stamina/attack/vital multipliers; `enrage` = lower/upper angry
  params + rate levels;
  `stamina` = exhaust params; `ride` = mount success vital;
  `partVitals` = per-part HP pools; `attacks` = shell-attack name catalog;
  `breakRewards` = break→reward-table linkage; `guild` = guild/HR points
  + zenny per hunt tier.

## Endemics (`data/endemics.json`, 70)

`EnemyReportAnimalData` habitats + EnemyData names. Species id 0 =
unclassified (all endemics); variants share one EM (toads, wasps,
beetles…) distinguished by EnemyData rows.

## Regenerating

Follow `datamine/README.md`. After a game patch, re-run the extraction
(base + patch chain merge) and `meat_all.py`; the validation step prints
the new match rate and every drifted cell. Then re-run steps 10–12 for
the guide/quest/size dataset.
