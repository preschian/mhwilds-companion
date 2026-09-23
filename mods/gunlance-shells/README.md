# GunlanceShells (MH Wilds)

Standalone REFramework QoL: every Gunlance gets **+10 shells** over its
native capacity. Each weapon keeps its own base count (a 6-shell weapon
becomes 16, an 8-shell weapon becomes 18); skills such as Load Shells
keep working on top of the native base.

## Install

Deploy with `.\scripts\deploy.ps1` (copies to the game's
`reframework\autorun\`), then **Reset Scripts** in REFramework (or
restart the game).

Requires `dinput8.dll` (REFramework) next to `MonsterHunterWilds.exe`.

## Usage

1. Launch the game and equip any Gunlance
2. The bonus applies on setup (equip, skill change, quest start)
3. Open Script Generated UI > GunlanceShells to toggle or change the
   bonus (1-50); changes take effect on the next reload

Disabling restores the native shell count on the next reload.

## How it works

Post-hooks on `app.cHunterWp07Handling`:

| Hook | Role |
|------|------|
| `setupLimitAmmo` | Raise the freshly recomputed native limit by the bonus |
| `reloadShell` | Re-apply after silent resets, live bonus changes, or disable |

Limits are read/written through `app.cAmmo` (`get/setLimitAmmo`,
`get/setLoadedAmmo`); the mod never touches the encrypted
`via.rds.Mandrake` fields directly. Per-weapon bases are tracked per
ammo instance, so repeated setups never stack the bonus.

## Notes

- Client-side only; other players are unaffected.
- After game patches, re-check the hooked methods if the bonus stops
  applying.
