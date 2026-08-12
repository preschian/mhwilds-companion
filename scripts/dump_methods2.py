import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
OUT = Path(r"D:\Workspace\mhwilds-companion\mods\fieldguide-sos\dump_slices\_methods2.txt")

print("loading...")
data = json.load(DUMP.open(encoding="utf-8", errors="ignore"))

# find related keys
needles = [
    "cSearchQuestSessionInfo.cTargetInfo",
    "cJoinQuestSessionInfo",
    "QuestMatchmake",
    "CurrentEnemy",
    "setCurrentEnemy",
    "RescueSearchTarget",
    "getRescueTargetInfo",
    "QuestSessionManager",
    "net_quest_session",
    "GUI040205",
]

keys = []
for k in data:
    if not isinstance(k, str) or not k.startswith("app."):
        continue
    if "<>" in k or "`" in k:
        continue
    if any(n in k for n in (
        "cSearchQuestSessionInfo",
        "cJoinQuestSessionInfo",
        "QuestMatchmake",
        "QuestSession",
        "net_quest_session",
        "GUIManager",
        "cGUIManager",
        "GUI040205",
        "QuestDef.QUEST_SEARCH",
    )):
        keys.append(k)

lines = ["==== matched keys"] + sorted(keys)

CORE = [
    "app.net_quest_session.cSearchQuestSessionInfo.cTargetInfo",
    "app.net_quest_session.cJoinQuestSessionInfo",
    "app.net_quest_session.cSessionInfo",
    "app.net_quest_session.QuestSessionManager",
    "app.net_session_manager.cSearchSessionInfo",
    "app.QuestDef.QUEST_SEARCH_PARAM_ROLE_ID",
    "app.GUI040200",
    "app.GUIManager",
    "app.cGUIManager",
    "app.GUIBaseApp",
]

# also include any key containing CurrentEnemy as method owner search via text scan of dumped types
for name in CORE + [k for k in keys if "TargetInfo" in k or "JoinQuest" in k or "QuestSession" in k][:40]:
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
        params = m.get("params") or []
        ps = ", ".join((p.get("type") if isinstance(p, dict) else str(p)) for p in params)
        ret = m.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        lines.append(f"  M {k}({ps}) -> {ret}")
    for k, f in sorted(fields.items()):
        if isinstance(f, dict):
            lines.append(f"  F {k}: {f.get('type')}")
    for k, p in sorted(props.items()):
        if isinstance(p, dict):
            lines.append(f"  P {k}")

# scan GUI040205* for CurrentEnemy field name
for name, obj in data.items():
    if not isinstance(name, str) or not name.startswith("app.GUI040205"):
        continue
    if not isinstance(obj, dict):
        continue
    fields = obj.get("fields") or {}
    if isinstance(fields, dict):
        for fk in fields:
            if "Current" in fk or "Enemy" in fk or "Select" in fk:
                lines.append(f"FIELDHIT {name}.{fk}: {fields[fk].get('type') if isinstance(fields[fk], dict) else fields[fk]}")

OUT.write_text("\n".join(lines), encoding="utf-8")
print("wrote", OUT)
