import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
OUT = Path(r"D:\Workspace\mhwilds-companion\mods\fieldguide-sos\dump_slices\_methods3.txt")
print("loading...")
data = json.load(DUMP.open(encoding="utf-8", errors="ignore"))
lines = []

NAMES = [
    "app.net_session_manager.SessionManager",
    "app.net_session_manager.SessionManager.cSearchResultQuest",
    "app.net_quest_session.cQuestSession",
    "app.QuestDef.QUEST_SEARCH_PARAM_ROLE_ID",
    "app.QuestDef.QUEST_SEARCH_PARAM_ROLE_ID_Fixed",
    "app.cGUIQuestOrderParam.QUEST_ORDER_FROM",
    "app.cGUIQuestOrderParam.QUEST_START_TYPE",
    "app.EnemyDef.ID_Fixed",
    "app.EnemyDef",
]

# find SessionManager / NetworkManager singletons-ish by name
extra = [k for k in data if isinstance(k, str) and k.startswith("app.") and ("SessionManager" in k or k == "app.NetworkManager" or "NetSession" in k or k.endswith(".NetworkRoot") or "GameManager" in k) and "<>" not in k and "`" not in k]
for name in NAMES + sorted(extra)[:40]:
    obj = data.get(name)
    if not obj:
        lines.append(f"==== MISS {name}")
        continue
    methods = obj.get("methods") or {}
    fields = obj.get("fields") or {}
    props = obj.get("properties") or {}
    lines.append(f"==== {name} m={len(methods)} f={len(fields)} parent={obj.get('parent')}")
    for k, m in sorted(methods.items()):
        if not isinstance(m, dict):
            continue
        low = k.lower()
        if not any(x in low for x in ("quest", "rescue", "rescure", "search", "join", "match", "get_", "set_", "instance", "singleton", "session", "depart", "accept", "auto")):
            continue
        params = m.get("params") or []
        ps = ", ".join((p.get("type") if isinstance(p, dict) else str(p)) for p in params)
        ret = m.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        lines.append(f"  M {k}({ps}) -> {ret}")
    for k, f in sorted(fields.items()):
        if isinstance(f, dict) and any(x in k.lower() for x in ("quest", "session", "match", "rescue", "instance")):
            lines.append(f"  F {k}: {f.get('type')}")
    # enums: print all fields
    if obj.get("parent") == "System.Enum":
        for k, f in sorted(fields.items()):
            if isinstance(f, dict):
                lines.append(f"  E {k}")

# getRescueTargetInfo full + acceptQuestFromSearchResult neighbors already known
# dump BossReportInfo fields fully
obj = data["app.GUI040205.BossReportInfo"]
lines.append("==== BossReportInfo ALL FIELDS")
for k, f in (obj.get("fields") or {}).items():
    if isinstance(f, dict):
        lines.append(f"  F {k}: {f.get('type')}")

# EnemyDef methods for ID conversion
obj = data.get("app.EnemyDef") or {}
lines.append(f"==== app.EnemyDef m={len(obj.get('methods') or {})}")
for k, m in sorted((obj.get("methods") or {}).items()):
    if not isinstance(m, dict):
        continue
    if any(x in k.lower() for x in ("fixed", "convert", "toid", "fromid", "getid", "emid")):
        params = m.get("params") or []
        ps = ", ".join((p.get("type") if isinstance(p, dict) else str(p)) for p in params)
        ret = m.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        lines.append(f"  M {k}({ps}) -> {ret}")

OUT.write_text("\n".join(lines), encoding="utf-8")
print("wrote", OUT, "lines", len(lines))
