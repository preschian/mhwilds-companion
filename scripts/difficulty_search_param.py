import json

data = json.load(open(r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json", encoding="utf-8", errors="ignore"))

for name in [
    "app.user_data.QuestDifficultySearchParamData",
    "app.user_data.QuestDifficultySearchParamData.cData",
    "app.cGUI050000MemberSettingItemData.cQuestDifficultyData",
    "app.GUI050000PartsBase.cRescueSearchSettingParamHolder",
]:
    obj = data.get(name) or {}
    print("====", name)
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        print(f"  M {mk}({ps}) -> {ret}")
    for fk, fv in sorted((obj.get("fields") or {}).items()):
        if isinstance(fv, dict):
            print(f"  F {fk}: {fv.get('type')} default={fv.get('default')}")

# QuestSession SearchResultTbl
print("==== SessionManager fields with Search")
obj = data.get("app.net_session_manager.SessionManager") or {}
for fk, fv in sorted((obj.get("fields") or {}).items()):
    if isinstance(fv, dict) and ("Search" in fk or "Result" in fk):
        print(f"  F {fk}: {fv.get('type')}")
for mk, mv in sorted((obj.get("methods") or {}).items()):
    if not isinstance(mv, dict):
        continue
    if "Search" in mk or "search" in mk:
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        print(f"  M {mk}({ps}) -> {ret}")

print("==== cQuestSession search/result")
obj = data.get("app.net_quest_session.cQuestSession") or {}
for mk, mv in sorted((obj.get("methods") or {}).items()):
    if not isinstance(mv, dict):
        continue
    if any(x in mk.lower() for x in ("search", "result", "rescure", "rescue", "filter")):
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        print(f"  M {mk}({ps}) -> {ret}")
for fk, fv in sorted((obj.get("fields") or {}).items()):
    if isinstance(fv, dict) and any(x in fk for x in ("Search", "Result", "Match", "Rescue")):
        print(f"  F {fk}: {fv.get('type')}")
