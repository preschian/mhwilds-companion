# Field Guide SOS (MH Wilds)

Standalone REFramework QoL: highlight a large monster in the Field Guide → **F1** → SOS search → auto join/depart.

## Install

Already deployed when using `.\scripts\deploy.ps1`.

Requires `dinput8.dll` (REFramework) next to `MonsterHunterWilds.exe`.

## Usage

1. Launch game, load into world (online)
2. Open **Large Monster Field Guide** (`GUI040205`)
3. Highlight a monster
4. Press **F1** — mod searches SOS for that target and tries auto join/depart
5. **F1** again or **Esc** cancels retry loop

Config: REFramework → Script Generated UI → FieldGuideSOS

## Files

| File | Role |
|------|------|
| `fieldguide_sos.lua` | Main mod |
| `fieldguide_sos_probe.lua` | Optional discovery helper (can remove after wiring) |

## Notes

- Join is best-effort against Capcom session APIs (`requestAutoJoinRescure` / search results).
- Departure point may still prompt depending on game state.
- After game patches, re-dump SDK if hooks break.
