# Datamine pipeline (MH Wilds)

Extracts monster data, per-part hitzones, and monster icons from a local
Monster Hunter Wilds install into `../data/` for the companion app.

Requires: Windows, Python 3.10+ (stdlib only), ~15 GB free temp space.
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

# 5. Full hitzone dataset + Kiranico cross-check report
python .\datamine\meat_all.py

# 6. Finalize data/monsters.json + data/icons/*.png (icons committed:
#    private repo only, Capcom assets)
python .\datamine\finalize.py
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

## Key findings (see `../docs/datamine.md`)

- Hitzones live in `GameDesign/Enemy/EmXXXX/VV/Data/*_Param_Parts.user.3`
  (`app.user_data.EmParamParts.cMeat`: Guid + 10×S32).
- RSZ type hash = murmur3-32 (seed `0xFFFFFFFF`) of the il2cpp class name.
- Array counts and single Object refs align to 4, not the native align.
- `PARTS_TYPE` values are stable S32 ids resolved via `EnemyPartsTypeName.msg`.
- `Em0160_50` (Guardian Arkveld) shares `Em0160_00` parts; `Em1062` is a
  debug dummy (HP 999999, no name, no icon); `EM0000` is the `?` placeholder.
- Validation vs Kiranico-derived data: 99.3% of normal-state cells match.
