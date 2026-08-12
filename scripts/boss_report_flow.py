import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
OUT = Path(r"D:\Workspace\mhwilds-companion\mods\fieldguide-sos\dump_slices\_boss_report_flow.txt")
print("loading...")
data = json.load(DUMP.open(encoding="utf-8", errors="ignore"))
lines = []

# All methods that take BossReportInfo
needle = "app.GUI040205.BossReportInfo"
for name, obj in data.items():
    if not isinstance(name, str) or not isinstance(obj, dict):
        continue
    methods = obj.get("methods") or {}
    if not isinstance(methods, dict):
        continue
    for mk, mv in methods.items():
        if not isinstance(mv, dict):
            continue
        params = mv.get("params") or []
        types = [p.get("type") for p in params if isinstance(p, dict)]
        if needle in types or any(needle in (t or "") for t in types):
            lines.append(f"{name}.{mk}({', '.join(types)})")

lines.append("==== GUI040200 enemy/report methods")
obj = data["app.GUI040200"]
for mk, mv in sorted((obj.get("methods") or {}).items()):
    if not isinstance(mv, dict):
        continue
    if any(x in mk.lower() for x in ("enemy", "report", "boss", "select", "040205", "open")):
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        lines.append(f"  {mk}({ps}) -> {ret}")

lines.append("==== GUI040200Accessor")
acc = data.get("app.GUI040200Accessor")
if acc:
    for mk, mv in sorted((acc.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        lines.append(f"  {mk}({ps}) -> {ret}")
    for fk, fv in sorted((acc.get("fields") or {}).items()):
        if isinstance(fv, dict):
            lines.append(f"  F {fk}: {fv.get('type')}")

# GUIID enum entries for 0402
lines.append("==== GUIID related to 0402 / EnemyReport")
guiid = data.get("app.GUIID.ID") or {}
fields = guiid.get("fields") or {}
for fk, fv in fields.items():
    if isinstance(fv, dict) and any(x in fk for x in ("0402", "EnemyReport", "HunterNote", "FIELD", "Report")):
        lines.append(f"  {fk} default={fv.get('default')}")

# cGUICommonMenu_EnemyReportBoss methods
lines.append("==== cGUICommonMenu_EnemyReportBoss")
obj = data.get("app.cGUICommonMenu_EnemyReportBoss") or {}
for mk, mv in sorted((obj.get("methods") or {}).items()):
    if isinstance(mv, dict):
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        lines.append(f"  {mk}({ps}) -> {ret}")

# Search for EnemyDef.ID params on GUI0402*
lines.append("==== GUI0402* methods with EnemyDef.ID param")
for name, obj in data.items():
    if not isinstance(name, str) or not name.startswith("app.GUI0402"):
        continue
    if not isinstance(obj, dict):
        continue
    for mk, mv in (obj.get("methods") or {}).items():
        if not isinstance(mv, dict):
            continue
        params = mv.get("params") or []
        types = [p.get("type") for p in params if isinstance(p, dict)]
        if any(t and "EnemyDef.ID" in t for t in types):
            lines.append(f"{name}.{mk}({', '.join(types)})")

OUT.write_text("\n".join(lines), encoding="utf-8")
print("wrote", OUT, "lines", len(lines))
