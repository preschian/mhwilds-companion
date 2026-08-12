# Agent notes

Write all repo docs, comments, UI copy, and commit messages in English.

## Layout

| What | Path |
|------|------|
| Mod | `mods/fieldguide-sos/fieldguide_sos.lua` |
| Deploy | `.\scripts\deploy.ps1` → game `reframework\autorun\` |
| Game | `D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds` |
| Variant matrix | `docs/high-rank-monster-variants.md` |
| Trace log | `reframework/data/fieldguide_sos_trace_v<VERSION>.txt` |

Steam AppID `2246340`. Do not commit `il2cpp_dump.json` or trace logs.

After Lua edits: deploy, then **Reset Scripts** in REFramework (or restart). Tick auto on `UpdateBehavior`, never net/SDK calls from `on_frame`.

## UX

Field Guide highlight (`GUI060102.get_TargetEmId`) → **F1** search/join/depart. Arkveld (`27`) is the fallback. **Esc** cancels. **F8**/**F9** start/stop the tracer.

Retries rotate enabled High Rank variants strongest-first: Arch-tempered → Tempered → Frenzied → normal. Tempered is `RoleId=0`, `LegendaryId=1` (not RoleId=2). HR difficulty `300`. Rescue category `12`. Search `QuestNo`/`mission` uses `INVALID` (`4294967295`).

## Golden flow

1. Open Alma (`requestQuestCounter(NORMAL)`) or reuse UI `161`
2. **Before** search: `setQuestListInCategory(12)`
3. `GUI050000.search` with `resc=true diff=300`
4. Wait `hasSR` → `updateQuestDetailWindow` → `decideQuest`
5. UI `162` + panels `169`+`170` → Accept & Depart (`callbackDecide`) / `orderQuest`
6. After `isResucureSession`: `decideDepartLate` if the link exists, then `QuestDepart`

The game may emit fail-search + category `NONE` even when `hasSR` is present. Treat as noise; keep waiting on the list.

## Do not

| Action | Why |
|--------|-----|
| `setQuestListInCategory(12)` **after** search | Hard crash |
| Rewrite `setQuestListCategory(NONE→12)` | Dirty state → crash on join/depart |
| `Invoke` the close Action on `openDialog_faildSearchQuest` | Breaks `wait_order` after `decideQuest` |
| `SearchRescure` / `AutoJoin` with nil/`create_delegate` callbacks | Crash |
| Premature `acceptQuestFromSearchResult`, `openCampMenu`, `syncQuestDepart` | Unstable / crash |

Safe popup handling while `suppress_popup`: skip `LOCAL_SESSION_NOT_FOUND` (`110002`) and skip `openDialog_faildSearchQuest` with `SKIP_ORIGINAL` only. No rewrite, no Invoke.
