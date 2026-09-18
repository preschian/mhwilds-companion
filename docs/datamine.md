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
| Struct database | `il2cpp_dump.json` (REFramework SDK dump, beside the exe) |

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

## Regenerating

Follow `datamine/README.md`. After a game patch, re-run the extraction
(base + patch chain merge) and `meat_all.py`; the validation step prints
the new match rate and every drifted cell.
