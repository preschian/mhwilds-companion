# Handoff — mhwilds-companion

Checkpoint: **FieldGuideSOS v1.5.0** berhasil dalam pengujian awal target Field Guide generik dan rotasi varian per monster tanpa crash. Seluruh jeda (`action`, post-search, order, dan depart) bernilai nol.

## Goal

QoL MH Wilds (REFramework Lua standalone): dari monster yang disorot di Field Guide → auto search SOS varian terkuat yang tersedia → accept → depart, tanpa klik manual panjang.

Eksperimen opt-in `StartupAutoJoin v0.1.6` mengotomatisasi startup native ke save slot pertama dan Recommended Lobby, termasuk logo startup dan Press Any Key. Ia memakai callback native `cGUICommonMenu_Lobby00` agar `NetworkRequestManager.autoMatching` benar-benar berjalan, lalu menonaktifkan runtime dan melepas referensi setelah title flow `FINISH_END`. Fitur tidak ikut `deploy.ps1` dan file yang terpasang saat ini dinonaktifkan sebagai `startup_autojoin.lua.off`; source `mods/fieldguide-sos/startup_autojoin.lua`, log per versi di `reframework/data/startup_autojoin_v<VERSION>.txt`.

Target UX: Field Guide highlight monster → **F1** → SOS search/accept/depart. `em_id=0` membaca snapshot `GUI060102.get_TargetEmId` saat F1; angka positif tetap menjadi override manual, dan Arkveld (`27`) menjadi fallback.

## Paths

| Apa | Path |
|-----|------|
| Repo | `D:\Workspace\mhwilds-companion` |
| Mod source | `mods\fieldguide-sos\fieldguide_sos.lua` |
| Deploy | `scripts\deploy.ps1` → `...\MonsterHunterWilds\reframework\autorun\` |
| Game | `D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds` |
| Trace log | `reframework\data\fieldguide_sos_trace_v<VERSION>.txt` (CWD REF = `reframework/data/`) |
| Probe (OFF) | `mods\fieldguide-sos\fieldguide_sos_probe.lua.off` |
| SDK dump | `il2cpp_dump.json` di folder game (jangan commit) |
| Dump slices | `mods\fieldguide-sos\dump_slices\` |

Steam AppID: `2246340`. GitHub account: **preschian**.

## Hotkeys

| Key | Aksi |
|-----|------|
| **F1** | Start / cancel auto |
| **F8** | Start passive trace log |
| **F9** | Stop log + write counts |
| **Esc** | Cancel auto |

Setelah edit script: **Reset Scripts** di REFramework, atau restart game.

## Config / ID penting

| Item | Nilai |
|------|-------|
| Arkveld `EnemyDef.ID` | `27` |
| Tempered | `RoleId=0`, `LegendaryId=1` (**bukan** RoleId=2) |
| Arkveld normal / Arch-tempered | `LegendaryId=0` / `LegendaryId=2` |
| HR search difficulty | `300` |
| Rescue category | `12` (`SERCH_RESCUE_SIGNAL`) |
| Alma / order / camp UI | `161` / `162` / `163` |
| Camp info panels | `169` + `170` |
| Field Guide large monster | `179` (`GUI060102`) |
| `LOCAL_SESSION_NOT_FOUND` | `110002` |
| `action_gap_s` / `post_search_settle_s` / `order_settle_s` / `depart_settle_s` | `0.0` / `0.0` / `0.0` / `0.0` |
| `mission` search | `INVALID` (`4294967295`) |

## Alur auto yang jalan (golden)

1. Buka Alma: `requestQuestCounter(NORMAL)` atau sudah open → UI `161`
2. **Sebelum** search: `setQuestListInCategory(12)` — **aman**
3. Snapshot `GUI060102.get_TargetEmId`, lalu `GUI050000.search` dengan `resc=true diff=300`; retry merotasi varian valid per monster: Arch-tempered → Tempered → Frenzied → normal
4. Game sering `setQuestListCategory(NONE)` + path fail-search dialog — **boleh di-skip**; hasil SOS tetap bisa ada (`hasSR`)
5. Tunggu list `hasSR` → `updateQuestDetailWindow` → settle → `decideQuest`
6. Tunggu UI `162` + panel `169`+`170` → `orderQuest` → join
7. Setelah `isResucureSession` → settle → `decideDepartLate` (jika ada link) → `QuestDepart`

## Crash / anti-pattern (jangan ulangi)

| Jangan | Kenapa |
|--------|--------|
| `setQuestListInCategory(12)` **setelah** search | Crash keras (log ~13:56) |
| REWRITE `setQuestListCategory(NONE→12)` | State kotor → crash di join/depart (1.4.5) |
| `Invoke` close Action di `openDialog_faildSearchQuest` | Memutus `wait_order` setelah `decideQuest` (1.4.6) |
| `SearchRescure` / `AutoJoin` + nil/`create_delegate` callback | Crash |
| Net call dari `on_frame` | Pakai `UpdateBehavior` / pola yang sudah ada |
| `acceptQuestFromSearchResult` prematur | Tidak stabil |
| `openCampMenu` / `syncQuestDepart` prematur | Crash |

## Popup handling (v1.4.7)

Yang **aman** (seperti 1.4.5 PREVENT, tanpa rewrite/invoke):

- Skip `NetworkErrorManager` error `LOCAL_SESSION_NOT_FOUND` (110002) saat `suppress_popup`
- Skip UI `openDialog_faildSearchQuest` (`SKIP_ORIGINAL`) — **tanpa** Invoke callback
- **Tidak** rewrite `setQuestListCategory`

Catatan: game tetap bisa emit “fail search” + category `NONE` meski list `hasSR` muncul. Anggap noise; lanjut wait list.

## Versi singkat

| Ver | Catatan |
|-----|---------|
| 1.4.4 | Full run sampai `AUTO DONE`; popup fail-search masih bisa muncul |
| 1.4.5 | Popup hilang (PREVENT + REWRITE) → crash saat depart/join akhir |
| 1.4.6 | Hapus REWRITE, tambah Invoke dismiss → stuck setelah decide |
| **1.4.7** | PREVENT saja + settle depart 1s + action gap 1s — **checkpoint ini** |

## Deploy

```powershell
.\scripts\deploy.ps1
# atau
Copy-Item mods\fieldguide-sos\fieldguide_sos.lua `
  "D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\reframework\autorun\" -Force
```

Launch: `steam://rungameid/2246340`

## Cara tes

1. Masuk dunia (online)
2. Reset Scripts → pastikan log `MOD LOADED v1.5.0`
3. F8 → F1 → F9
4. Sukses = log sampai `===== AUTO DONE =====` tanpa crash
5. Kalau gagal: kirim potongan `AUTO START` → akhir dari `fieldguide_sos_trace_v<VERSION>.txt`

## Next (prioritas)

1. Skip quest yang sudah full
2. Validasi mode Field Guide (`em_id=0`) dengan monster non-Arkveld
3. Optional: auto-open Alma polish / retry search lebih pintar

## Agent context

- Transcript sesi panjang: Cursor agent transcripts project `D-Workspace-mhwilds-companion` (cari session FieldGuideSOS / SOS)
- Bahasa user: Indonesia
- Probe biarkan **off** kecuali discovery baru
- Jangan commit `il2cpp_dump.json` / trace log
