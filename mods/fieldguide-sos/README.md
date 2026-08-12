# Field Guide SOS (MH Wilds)

Standalone REFramework QoL: **F1** → SOS search → auto join/depart. The default
target is the monster highlighted in the Field Guide. Search retries use only
the High Rank variants available for that monster.

## Install

Already deployed when using `.\scripts\deploy.ps1`.

Requires `dinput8.dll` (REFramework) next to `MonsterHunterWilds.exe`.

## Usage

1. Launch game, load into world (online)
2. Highlight a large monster in the Field Guide
3. Press **F1** — mod searches SOS for that monster and tries auto join/depart
4. **F1** again or **Esc** cancels retry loop

Target is always the highlighted Field Guide monster (`GUI060102`). If none can
be read, F1 errors with `no Field Guide target` and does not search. Join uses
native **Accept & Depart**.

The native matchmaking request accepts only one target state at a time. Retries
rotate through enabled variants from strongest to weakest: Arch-tempered →
Tempered → Frenzied → normal. Uncheck a variant in Script Generated UI →
FieldGuideSOS to skip it. Unsupported variants are still skipped per monster.

## Files

| File | Role |
|------|------|
| `fieldguide_sos.lua` | Main mod |
| `../../docs/high-rank-monster-variants.md` | High Rank variant matrix |

## Notes

- Join is best-effort against Capcom session APIs (`search` / search results).
- Departure point may still prompt depending on game state.
- After game patches, re-dump SDK if hooks break.
