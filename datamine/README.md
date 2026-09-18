# Datamine pipeline (MH Wilds)

Extracts monster data, per-part hitzones, and monster icons from a local
Monster Hunter Wilds install into `../data/` for the companion app.

Requires: Windows, Python 3.10+ (stdlib only; Pillow needed just for
step 8: `pip install pillow`), ~15 GB free temp space.
Set `MHRESEARCH` to override the work dir (default: `%TEMP%\mhwilds-research`),
`MHWILDS_GAME` to override the game dir.

## Run

```powershell
# 1. Third-party tools (REToolCustom, MHWs.list, texconv)
.\datamine\fetch_tools.ps1

# 2. Extract enemy data + name banks from base pak + patch chain (~20-40 min),
#    merged newest-wins into $MHRESEARCH\extract_full\merged
.\datamine\extract_full.ps1

# 3. Extract icon textures from the streaming pak + patches, merge
#    newest-wins, convert TEX->DDS->PNG
.\datamine\extract_icons.ps1
.\datamine\build_icons.ps1

# 4. Name maps
python .\datamine\build_partnames.py
$R = $env:MHRESEARCH; if (-not $R) { $R = Join-Path $env:TEMP 'mhwilds-research' }
python .\datamine\enum_dump.py 'app.EnemyDef.PARTS_TYPE' 'app.Hit.ROD_EXTRACT' > (Join-Path $R 'parts_enums.json')
python .\datamine\msg_parse.py (Join-Path $R 'extract_full\merged\natives\STM\GameDesign\Text\Excel_Data\EnemyText.msg.23') --json (Join-Path $R 'enemy_text_merged.json')
python .\datamine\msg_parse.py (Join-Path $R 'extract_full\merged\natives\STM\GameDesign\Text\Excel_Data\Item.msg.23') --json (Join-Path $R 'item_text.json')

# 5. Full hitzone dataset (+ Kiranico cross-check if the optional reference
#    clone exists under $MHRESEARCH; otherwise validation is skipped)
#    Reference: https://github.com/sockbats/MH-Wilds-Monster-Database
python .\datamine\meat_all.py

# 6. Finalize data/monsters.json + data/icons/*.png (icons committed:
#    private repo only, Capcom assets)
python .\datamine\finalize.py

# 7. Rewards: parse per-monster reward tables + item catalog, extend
#    monsters.json with rewards, write data/materials.json (includes a
#    Rathian wiki-oracle self-check)
python .\datamine\reward_all.py
python .\datamine\reward_finalize.py

# 8. Item icons: extract glyph/badge atlases + AddIconData + tint palette,
#    parse icon fields, crop 77 glyphs + 5 badges
.\datamine\extract_itemicons.ps1
.\datamine\build_itemicons.ps1
python .\datamine\itemicons_all.py

# 9. Finalize data/icons/items/*.png + data/item_palette.json, merge icon
#    fields into data/materials.json
python .\datamine\itemicons_finalize.py

# 10. Guide/mission extraction (Field Guide tables, 291 missions, texts)
.\datamine\extract_guide.ps1

# 11. Parse extras + missions + guide tables into $MHRESEARCH JSONs
python .\datamine\monster_extra.py
python .\datamine\mission_all.py
python .\datamine\guide_all.py

# 12. Merge into data/monsters.json + data/quests.json +
#     data/endemics.json + data/guide_meta.json
python .\datamine\guide_finalize.py
```

`il2cpp_dump.json` (REFramework SDK dump, 2 GB) must exist next to the game
exe; it is the struct database for the RSZ reader. It is never committed.

## Scripts

| File | Role |
|------|------|
| `fetch_tools.ps1` | Download REToolCustom, MHWs.list, texconv |
| `extract_full.ps1` | PAK extract (base + patches) + newest-wins merge |
| `extract_icons.ps1` | Icon texture extract (streaming pak + patches) |
| `build_icons.ps1` | Icon merge + TEX→DDS→PNG batch |
| `msg_parse.py` | GMSG `.msg` reader (XOR decrypt + entries) |
| `build_partnames.py` | Part-type-id → English map from msg |
| `rsz_read.py` | Generic RSZ data reader (il2cpp layouts) |
| `rsz_inspect.py` | RSZ header/instance/userData dump + murmur3 |
| `rsz_classscan.py` | Resolve instance hashes → class names |
| `dump_block.py` / `dump_rsz.py` / `enum_dump.py` | il2cpp_dump miners |
| `hash_check.py` | murmur3(class) calculator + collision finder |
| `meat_extract.py` | One monster: `EmXXXX VV` → hitzone printout |
| `meat_all.py` | All monsters → `monsters.json` + validation |
| `finalize.py` | Add category/icon, copy PNGs to `data/` |
| `reward_all.py` | Parse reward tables + item catalog → `rewards.json` |
| `reward_finalize.py` | Merge rewards into dataset + `materials.json` |
| `extract_itemicons.ps1` | Item atlas + AddIconData + palette extract |
| `build_itemicons.ps1` | Atlas merge + TEX→DDS→PNG batch |
| `itemicons_all.py` | Icon fields + palette parse, glyph/badge crop |
| `itemicons_finalize.py` | `data/icons/items/` + palette + `materials.json` icons |
| `extract_guide.ps1` | Guide/mission/text extract (`lists/*.list`) + merge |
| `monster_extra.py` | RSZ auto-parse + extras/texts/sizes → research JSONs |
| `mission_all.py` | 291 missions → `mission_index.json` |
| `guide_all.py` | Guide tables + texts → `guide.json` |
| `guide_finalize.py` | Merge → `monsters.json` + `quests/endemics/guide_meta.json` |

## Key findings (see `../docs/datamine.md`)

- Hitzones live in `GameDesign/Enemy/EmXXXX/VV/Data/*_Param_Parts.user.3`
  (`app.user_data.EmParamParts.cMeat`: Guid + 10×S32).
- RSZ type hash = murmur3-32 (seed `0xFFFFFFFF`) of the il2cpp class name.
- Array counts and single Object refs align to 4, not the native align.
- `PARTS_TYPE` values are stable S32 ids resolved via `EnemyPartsTypeName.msg`.
- `Em0160_50` (Guardian Arkveld) shares `Em0160_00` parts; `Em1062` is a
  debug dummy (HP 999999, no name, no icon); `EM0000` is the `?` placeholder.
- Validation vs Kiranico-derived data: 99.3% of normal-state cells match.
- Rewards live in `GameDesign/Common/Enemy/EM*.user.3` (`EnemyRewardData`):
  dataId hundreds = category (1xx carve, 2xx tail, 3xx break, 4xx wound,
  5xx target rolls, 6xx bonus), story slots = low rank, ex arrays = high
  rank. Breaks link via partsIndex == RewardTableIndex. Item names from
  `Item.msg.23` (`Item_IT_<id>`).
- Item icons are composite: base glyph (atlas cell `max(0, IconType-1)`
  in `tex000201_0`) × tint (`ColorPreset.TYPE` → `colorPreset.gcp.2`
  slot 0) + corner badge (`AddIconData` pattern → `tex000201_20` cell).
