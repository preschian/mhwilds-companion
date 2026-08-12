# Field Guide SOS (MH Wilds)

Standalone REFramework QoL: **F1** → SOS search → auto join/depart. The default
target cycles through Arch-tempered, Tempered, and normal Arkveld; Field Guide
targeting is available as an option.

## Install

Already deployed when using `.\scripts\deploy.ps1`.

Requires `dinput8.dll` (REFramework) next to `MonsterHunterWilds.exe`.

## Usage

1. Launch game, load into world (online)
2. Press **F1** — mod searches SOS for any Arkveld variant and tries auto join/depart
3. **F1** again or **Esc** cancels retry loop

Config: REFramework → Script Generated UI → FieldGuideSOS. The default `em_id=27`
targets Arkveld. Set `em_id=0`, open `GUI060102`, and highlight a monster to use
the Field Guide target; any other positive ID is a manual override.

The native matchmaking request accepts only one target state at a time. For
Arkveld, retries rotate in this order: Arch-tempered → Tempered → normal.

`accept_and_depart` uses the game's native **Accept & Depart** action. Disable it
to retain the **Accept & Prep** flow followed by the mod's separate depart action.

## Files

| File | Role |
|------|------|
| `fieldguide_sos.lua` | Main mod |
| `fieldguide_sos_probe.lua` | Optional discovery helper (can remove after wiring) |

## Notes

- Join is best-effort against Capcom session APIs (`search` / search results).
- Departure point may still prompt depending on game state.
- After game patches, re-dump SDK if hooks break.
