import json
from pathlib import Path

DUMP = Path(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json")
data = json.load(DUMP.open(encoding="utf-8", errors="ignore"))

def dump(name):
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj: return
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict): continue
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict): ret = ret.get("type")
        print(f"  M {mk}({ps}) -> {ret}")
    for fk, fv in sorted((obj.get("fields") or {}).items()):
        if isinstance(fv, dict):
            print(f"  F {fk}: {fv.get('type')} default={fv.get('default')}")

for n in [
    "app.GUIUtilApp.QuestUtil",
    "app.net_quest_session.cSearchQuestSessionInfo",
    "app.net_quest_session.cSearchQuestSessionInfo.cTargetInfo",
    "app.QuestDef.QUEST_SEARCH_PARAM_ROLE_ID",
    "app.EnemyDef.LEGENDARY_ID",
    "app.EnemyDef.ROLE_ID",
    "app.net_session_manager.SESSION_TYPE",
    "app.GUI050000PartsBase.cRescueSearchSettingParamHolder",
    "app.net_quest_session.cQuestSession",
]:
    dump(n)

# EnemyDef conversion methods
obj = data.get("app.EnemyDef") or {}
print("==== app.EnemyDef convert/id methods")
for mk, mv in sorted((obj.get("methods") or {}).items()):
    if not isinstance(mv, dict): continue
    if any(x in mk.lower() for x in ("fixed", "convert", "toid", "from", "getid", "legendary", "role", "rescue", "search")):
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict): ret = ret.get("type")
        print(f"  M {mk}({ps}) -> {ret}")
