# High Rank Monster Variants

Captured from Monster Hunter Wilds' enabled SOS target list on 2026-08-12.
The capture reflects the installed game version and the monsters unlocked by the
current save.

## Summary

- 34 unique large-monster IDs
- 74 searchable monster/variant combinations
- 34 normal entries
- 5 Frenzied entries
- 30 Tempered entries
- 5 Arch-tempered entries

The three non-monster target entries (`Any`, `Delivery`, and `Small Monsters`)
are excluded.

## Search fields

| Variant | Search role | `cTargetInfo.RoleId` | `cTargetInfo.LegendaryId` |
|---|---:|---:|---:|
| Normal | 0 (`NORMAL`) | 0 (`NORMAL`) | 0 (`NONE`) |
| Frenzied | 1 (`FRENZY`) | 3 (`FRENZY`) | 0 (`NONE`) |
| Tempered | 2 (`LEGENDARY`) | 0 (`NORMAL`) | 1 (`NORMAL`) |
| Arch-tempered | 3 (`KING`) | 0 (`NORMAL`) | 2 (`KING`) |

## Monsters

| EmID | Monster | Normal | Frenzied | Tempered | Arch-tempered |
|---:|---|:---:|:---:|:---:|:---:|
| 0 | Rathian | Yes | — | Yes | — |
| 1 | Rathalos | Yes | — | Yes | — |
| 2 | Guardian Rathalos | Yes | — | Yes | — |
| 3 | Gravios | Yes | — | Yes | — |
| 4 | Yian Kut-Ku | Yes | Yes | Yes | — |
| 5 | Gypceros | Yes | Yes | Yes | — |
| 6 | Congalala | Yes | — | Yes | — |
| 7 | Blangonga | Yes | Yes | Yes | — |
| 8 | Lagiacrus | Yes | — | Yes | — |
| 9 | Nerscylla | Yes | Yes | Yes | — |
| 10 | Gore Magala | Yes | — | Yes | — |
| 11 | Seregios | Yes | — | Yes | — |
| 12 | Gogmazios | Yes | — | — | — |
| 13 | Mizutsune | Yes | — | Yes | — |
| 14 | Guardian Fulgur Anjanath | Yes | — | Yes | — |
| 15 | Guardian Ebony Odogaron | Yes | — | Yes | — |
| 16 | Doshaguma | Yes | — | Yes | — |
| 17 | Guardian Doshaguma | Yes | — | Yes | — |
| 18 | Balahara | Yes | — | Yes | — |
| 19 | Chatacabra | Yes | — | Yes | — |
| 20 | Quematrice | Yes | — | Yes | — |
| 21 | Lala Barina | Yes | — | Yes | — |
| 22 | Rompopolo | Yes | — | Yes | — |
| 23 | Rey Dau | Yes | — | Yes | Yes |
| 24 | Uth Duna | Yes | — | Yes | Yes |
| 25 | Nu Udra | Yes | — | Yes | Yes |
| 26 | Ajarakan | Yes | — | Yes | — |
| 27 | Arkveld | Yes | — | Yes | Yes |
| 28 | Guardian Arkveld | Yes | — | — | — |
| 29 | Hirabami | Yes | Yes | Yes | — |
| 30 | Jin Dahaad | Yes | — | Yes | Yes |
| 31 | Xu Wu | Yes | — | Yes | — |
| 32 | Zoh Shia | Yes | — | — | — |
| 34 | Omega Planetes | Yes | — | — | — |

## Implementation note

Guardian forms use distinct `EmID` values and must not be treated as legendary
levels of their base monsters. A generic Field Guide search should build its
variant list from the exact combinations above and search from the strongest
available variant down to normal.
