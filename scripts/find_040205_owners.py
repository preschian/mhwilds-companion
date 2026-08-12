import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
data = json.load(DUMP.open(encoding="utf-8", errors="ignore"))
out = []

# types that reference GUI040205 or PartsEnemyList as field/return
needles = {
    "app.GUI040205",
    "app.GUI040205PartsEnemyList",
    "app.GUI040205PartsEnemyDetail",
    "app.GUI040200PartsEnemyReport",
}
for name, obj in data.items():
    if not isinstance(name, str) or not name.startswith("app.") or "<>" in name or "`" in name:
        continue
    if not isinstance(obj, dict):
        continue
    hits = []
    for fk, fv in (obj.get("fields") or {}).items():
        if isinstance(fv, dict) and fv.get("type") in needles:
            hits.append(f"F {fk}:{fv.get('type')}")
    for mk, mv in (obj.get("methods") or {}).items():
        if not isinstance(mv, dict):
            continue
        ret = mv.get("returns")
        rtype = ret.get("type") if isinstance(ret, dict) else ret
        if rtype in needles:
            hits.append(f"M {mk}->{rtype}")
        for p in mv.get("params") or []:
            if isinstance(p, dict) and p.get("type") in needles:
                hits.append(f"M {mk} param {p.get('type')}")
    if hits:
        out.append(name)
        out.extend("  " + h for h in hits[:20])

# Also dump GUI060102 briefly - in-field monster guide
out.append("==== GUI060102 methods with Enemy/select")
obj = data.get("app.GUI060102") or {}
for mk, mv in sorted((obj.get("methods") or {}).items()):
    if not isinstance(mv, dict):
        continue
    if any(x in mk.lower() for x in ("enemy", "select", "current", "emid", "target", "open")):
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        out.append(f"  {mk}({ps}) -> {ret}")

Path(r"D:\Workspace\mhwilds-companion\mods\fieldguide-sos\dump_slices\_owners.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out[:120]))
