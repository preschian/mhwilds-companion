import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)

for name in [
    "app.GUI050000QuestListParts",
    "app.cGUIQuestViewData",
    "app.net_session_manager.SessionManager.cSearchResultTblQuest",
    "ace.cLimitedArray`1<app.net_session_manager.SessionManager.cSearchResultQuest>",
]:
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        # try find limited array variants
        if "LimitedArray" in name:
            for k in data:
                if isinstance(k, str) and "cLimitedArray" in k and "SearchResultQuest" in k:
                    print(" found", k)
                    obj = data[k]
                    name = k
                    break
        if not obj:
            continue
    print(" parent", obj.get("parent"))
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        params = mv.get("params") or []
        ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
        ret = mv.get("returns")
        if isinstance(ret, dict):
            ret = ret.get("type")
        if any(
            x in mk.lower()
            for x in (
                "decide",
                "select",
                "get_",
                "set_",
                "update",
                "search",
                "result",
                "list",
                "item",
                "count",
                "front",
                "accept",
                "view",
            )
        ):
            print(f"  M {mk}({ps}) -> {ret}")
    for fk, fv in sorted((obj.get("fields") or {}).items()):
        if isinstance(fv, dict):
            print(f"  F {fk}: {fv.get('type')}")

print("==== keys with SearchResult / QuestView")
for k in sorted(data):
    if not isinstance(k, str):
        continue
    if "050000" in k and ("Search" in k or "Result" in k or "Rescue" in k):
        print(k)
    if "cGUIQuestViewData" in k:
        print(k)
