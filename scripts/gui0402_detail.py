import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
data = json.load(DUMP.open(encoding="utf-8", errors="ignore"))
out = []

keys = sorted(k for k in data if isinstance(k, str) and ("040200" in k or "040205" in k or "EnemyReportBoss" in k or "WidgetEm" in k) and k.startswith("app.") and "<>" not in k and "`" not in k)
out.append("==== keys")
out.extend(keys)

for name in [
    "app.GUI040200PartsEnemyReport",
    "app.cGUI040200WidgetEmCount",
    "app.GUI040200Accessor",
    "app.cGUICommonMenu_EnemyReportBoss",
    "app.GUI040208",
]:
    obj = data.get(name)
    out.append(f"==== {name} {'MISS' if not obj else ''}")
    if not obj:
        continue
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        out.append(f"  M {mk}({ps}) -> {ret}")
    for fk, fv in sorted((obj.get("fields") or {}).items()):
        if isinstance(fv, dict):
            out.append(f"  F {fk}: {fv.get('type')}")

# GUIID names containing 0402
guiid = data.get("app.GUIID.ID") or {}
out.append("==== GUIID.ID 0402*")
for fk, fv in (guiid.get("fields") or {}).items():
    if isinstance(fv, dict) and "0402" in fk:
        out.append(f"  {fk} = {fv.get('default')}")

Path(r"D:\Workspace\mhwilds-companion\mods\fieldguide-sos\dump_slices\_gui0402.txt").write_text("\n".join(out), encoding="utf-8")
print("keys", len(keys))
print("\n".join(out[:80]))
