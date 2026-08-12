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

Config: REFramework → Script Generated UI → FieldGuideSOS. The default `em_id=0`
uses the highlighted `GUI060102` monster. Any positive ID is a manual override;
Arkveld (`27`) remains the fallback when no Field Guide target can be read.

The native matchmaking request accepts only one target state at a time. Retries
rotate through available variants from strongest to weakest: Arch-tempered →
Tempered → Frenzied → normal. Unsupported variants are skipped per monster.

`accept_and_depart` uses the game's native **Accept & Depart** action. Disable it
to retain the **Accept & Prep** flow followed by the mod's separate depart action.

## Files

| File | Role |
|------|------|
| `fieldguide_sos.lua` | Main mod |
| `startup_autojoin.lua` | Experimental opt-in: Auto Start Game → save slot 1 → Recommended Lobby (not deployed by `deploy.ps1`) |
| `fieldguide_sos_probe.lua` | Optional discovery helper (can remove after wiring) |
| `monster_variant_probe.lua.off` | Disabled SOS target-list capture helper |
| `startup_flow_probe.lua.off` | Disabled title/startup flow capture helper |
| `../../docs/high-rank-monster-variants.md` | Captured High Rank variant matrix |

## Notes

- Join is best-effort against Capcom session APIs (`search` / search results).
- Departure point may still prompt depending on game state.
- After game patches, re-dump SDK if hooks break.
