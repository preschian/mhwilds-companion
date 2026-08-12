import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)

for name in [
    "app.cGUI050000QuestSearchWindowCtrl",
    "app.GUI050000",
    "app.cGUI050000ViewFlow.Flow.SearchQuest",
    "app.cGUI050000ViewFlow.cGUI050000ViewFlowBase",
]:
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        continue
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        ml = mk.lower()
        if any(
            x in ml
            for x in (
                "search",
                "accept",
                "select",
                "join",
                "result",
                "success",
                "fail",
                "order",
                "depart",
                "decide",
                "decide",
                "confirm",
                "rescue",
                "open",
            )
        ):
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            print(f"  M {mk}({ps}) -> {ret}")
    for fk, fv in sorted((obj.get("fields") or {}).items()):
        if isinstance(fv, dict) and any(
            x in fk.lower()
            for x in ("search", "result", "quest", "select", "list", "ctrl")
        ):
            print(f"  F {fk}: {fv.get('type')}")

print("==== acceptQuest / selectSearch refs")
for k, obj in data.items():
    if not isinstance(k, str) or not isinstance(obj, dict):
        continue
    if "050000" not in k and "SearchResult" not in k and "GUIManager" not in k:
        continue
    for mk, mv in (obj.get("methods") or {}).items():
        if not isinstance(mv, dict):
            continue
        ml = mk.lower()
        if any(
            x in ml
            for x in (
                "acceptquest",
                "selectresult",
                "selectsearch",
                "onselect",
                "decidequest",
                "orderquest",
                "joinsession",
            )
        ):
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            print(f"{k}.{mk}({ps}) -> {ret}")
