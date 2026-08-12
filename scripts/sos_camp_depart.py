import json

data = json.load(
    open(
        r"D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds\il2cpp_dump.json",
        encoding="utf-8",
        errors="ignore",
    )
)

keywords = (
    "camp",
    "depart",
    "accept",
    "order",
    "prepare",
    "ready",
    "decide",
    "rescue",
    "questorder",
    "opensession",
    "startquest",
    "syncquest",
)

for name in [
    "app.GUI050000QuestListParts",
    "app.GUIManager",
    "app.cGUIQuestOrderParam",
    "app.GUIFlowQuestCounter",
    "app.QuestCounterGUIContext",
    "app.cGUIQuestViewData",
    "app.cGUIQuestViewData.cGUISessionData",
]:
    obj = data.get(name)
    print("====", name, "MISS" if not obj else "")
    if not obj:
        continue
    for mk, mv in sorted((obj.get("methods") or {}).items()):
        if not isinstance(mv, dict):
            continue
        ml = mk.lower()
        if any(x in ml for x in keywords):
            params = mv.get("params") or []
            ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
            ret = mv.get("returns")
            if isinstance(ret, dict):
                ret = ret.get("type")
            if len(ps) < 140:
                print(f"  M {mk}({ps}) -> {ret}")
    for fk, fv in sorted((obj.get("fields") or {}).items()):
        if not isinstance(fv, dict):
            continue
        fl = fk.lower()
        if any(x in fl for x in ("camp", "order", "session", "accept", "depart", "quest")):
            print(f"  F {fk}: {fv.get('type')}")

print("==== cGUISessionData + SearchResult bridge")
for k, obj in data.items():
    if not isinstance(k, str) or not isinstance(obj, dict):
        continue
    if "cGUISessionData" in k or (
        "050000" in k and ("Camp" in k or "Accept" in k or "Depart" in k or "Order" in k)
    ):
        print(k)
        for mk, mv in sorted((obj.get("methods") or {}).items()):
            if not isinstance(mv, dict):
                continue
            if any(x in mk.lower() for x in keywords):
                params = mv.get("params") or []
                ps = ", ".join(p.get("type") for p in params if isinstance(p, dict))
                ret = mv.get("returns")
                if isinstance(ret, dict):
                    ret = ret.get("type")
                print(f"  M {mk}({ps}) -> {ret}")
        for fk, fv in (obj.get("fields") or {}).items():
            if isinstance(fv, dict):
                print(f"  F {fk}: {fv.get('type')}")
